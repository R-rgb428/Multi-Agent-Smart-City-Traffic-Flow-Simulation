"""Decision queue, Dijkstra alternative evaluator, operator actions, and oversight tracking."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import heapq
from typing import Dict, List, Optional, Tuple, Any

from agents.vehicle import VehicleAgent
from road_network.network import RoadNetwork, RoadSegment
from simulation.engine import SimulationEngine

K_CONGESTION = 3.5
ENERGY_KWH_PER_SEC_SAVED = 0.0085
MIN_SAVING_SEC = 5.0
CHECK_INTERVAL_TICKS = 3
MAX_PENDING_DECISIONS = 8
COOLDOWN_TICKS = 12


class ApiError(Exception):
    """Domain error mapped cleanly to HTTP status and {'error': message}."""
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _format_utc_clock() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def _dijkstra_occupancy_cost(
    network: RoadNetwork,
    origin: str,
    destination: str,
    k: float = K_CONGESTION,
) -> Tuple[float, List[str]]:
    """
    Shortest path using edge weight = free_flow_time * (1 + k * occupancy^2).
    Matches handoff/api-contract.md decision rule.
    """
    if origin == destination:
        return 0.0, [origin]
    if origin not in network.nodes or destination not in network.nodes:
        return float("inf"), []

    pq: List[Tuple[float, str, List[str]]] = [(0.0, origin, [origin])]
    best: Dict[str, float] = {origin: 0.0}

    while pq:
        cost, node, path = heapq.heappop(pq)
        if node == destination:
            return cost, path
        if cost > best.get(node, float("inf")):
            continue
        for road in network.get_outgoing_roads(node):
            occ = road.density
            weight = road.free_flow_time * (1.0 + k * (occ ** 2))
            nxt_cost = cost + max(0.1, weight)
            if nxt_cost < best.get(road.end_node, float("inf")):
                best[road.end_node] = nxt_cost
                heapq.heappush(pq, (nxt_cost, road.end_node, path + [road.end_node]))

    return float("inf"), []


def _route_occupancy_cost(network: RoadNetwork, nodes: List[str], k: float = K_CONGESTION) -> Tuple[float, List[RoadSegment]]:
    total = 0.0
    roads: List[RoadSegment] = []
    for i in range(len(nodes) - 1):
        road = network.get_road_between(nodes[i], nodes[i + 1])
        if not road:
            return float("inf"), []
        roads.append(road)
        occ = road.density
        total += road.free_flow_time * (1.0 + k * (occ ** 2))
    return total, roads


def _decision_anchor(vehicle: VehicleAgent) -> Tuple[Optional[str], int]:
    """Returns (decision_node, start_index_in_selected_route) suitable for update_route."""
    if vehicle.completion_status == "EN_ROUTE":
        if not vehicle.target_node:
            return None, -1
        return vehicle.target_node, vehicle.route_index + 1
    if vehicle.completion_status in ("WAITING", "PENDING"):
        return vehicle.current_node, vehicle.route_index
    return None, -1


@dataclass
class TrackedOutcome:
    decision_id: str
    vehicle_id: str
    predicted_saving_sec: float
    baseline_est_total_sec: float
    settled: bool = False
    succeeded: bool = False


class DecisionStore:
    """Manages reviewable AI decisions, operator actions, oversight KPIs, and activity log."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._counter = 1000
        self._decisions: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []
        self._cooldown_until: Dict[str, int] = {}
        self._activity: List[Dict[str, Any]] = []
        self._outcomes: Dict[str, TrackedOutcome] = {}
        self._stats_delay_saved: float = 0.0
        self._stats_queue_avoided: int = 0
        self._stats_energy_kwh: float = 0.0

    def _next_id(self) -> str:
        self._counter += 1
        return f"R-{self._counter}"

    def _historical_success_pct(self) -> int:
        settled = [o for o in self._outcomes.values() if o.settled]
        if not settled:
            return 88
        wins = sum(1 for o in settled if o.succeeded)
        return int(round((wins / len(settled)) * 100))

    def _refresh_outcomes(self, engine: SimulationEngine) -> None:
        """Marks pending decisions stale if completed and settles outcomes for approved/modified routes."""
        to_prune: List[str] = []
        for dec_id, dec in self._decisions.items():
            veh = engine.fleet_manager.vehicles.get(dec["vehicleId"])
            if not veh:
                continue
            if dec["status"] == "pending" and veh.completion_status == "COMPLETED":
                to_prune.append(dec_id)
                continue
            outcome = self._outcomes.get(dec_id)
            if outcome and not outcome.settled and veh.completion_status == "COMPLETED":
                outcome.settled = True
                outcome.succeeded = veh.travel_time <= (outcome.baseline_est_total_sec + 5.0)

        for dec_id in to_prune:
            self._decisions.pop(dec_id, None)
            if dec_id in self._order:
                self._order.remove(dec_id)

    def evaluate_tick(self, engine: SimulationEngine, force: bool = False) -> None:
        """Evaluates active vehicles every CHECK_INTERVAL_TICKS and emits pending Decisions."""
        self._refresh_outcomes(engine)

        if not force and engine.tick % CHECK_INTERVAL_TICKS != 0:
            return

        pending_vehicles = {
            d["vehicleId"] for d in self._decisions.values() if d["status"] == "pending"
        }
        pending_count = len(pending_vehicles)
        if pending_count >= MAX_PENDING_DECISIONS:
            return

        # Measure how populated the network is so confidence shrinks on sparse telemetry
        active_roads = sum(1 for r in engine.network.roads.values() if r.vehicle_count > 0 or r.queue_length > 0)
        telemetry_completeness = min(1.0, active_roads / max(6.0, len(engine.network.roads) * 0.25))

        candidates: List[Tuple[float, Dict[str, Any]]] = []

        for veh in engine.fleet_manager.vehicles.values():
            if veh.completion_status not in ("EN_ROUTE", "WAITING"):
                continue
            if veh.vehicle_id in pending_vehicles:
                continue
            if engine.tick < self._cooldown_until.get(veh.vehicle_id, 0):
                continue

            anchor, start_idx = _decision_anchor(veh)
            if not anchor or anchor == veh.destination:
                continue
            remaining = veh.selected_route[start_idx:]
            if len(remaining) < 2:
                continue

            cur_cost, cur_roads = _route_occupancy_cost(engine.network, remaining)
            if not cur_roads or cur_cost == float("inf"):
                continue

            alt_cost, alt_path = _dijkstra_occupancy_cost(engine.network, anchor, veh.destination)
            if len(alt_path) < 2 or alt_path == remaining or alt_cost == float("inf"):
                continue

            saving = cur_cost - alt_cost
            if saving <= MIN_SAVING_SEC:
                continue

            alt_roads = [
                engine.network.get_road_between(alt_path[i], alt_path[i + 1])
                for i in range(len(alt_path) - 1)
            ]
            alt_roads = [r for r in alt_roads if r is not None]

            payload = self._build_decision_payload(
                engine=engine,
                veh=veh,
                anchor=anchor,
                remaining=remaining,
                alt_path=alt_path,
                cur_roads=cur_roads,
                alt_roads=alt_roads,
                cur_cost=cur_cost,
                alt_cost=alt_cost,
                saving=saving,
                telemetry_completeness=telemetry_completeness,
            )
            candidates.append((saving, payload))

        candidates.sort(key=lambda item: item[0], reverse=True)
        slots_left = MAX_PENDING_DECISIONS - pending_count
        for _, payload in candidates[:slots_left]:
            dec_id = self._next_id()
            payload["id"] = dec_id
            payload["historicalSuccessPct"] = self._historical_success_pct()
            self._decisions[dec_id] = payload
            self._order.insert(0, dec_id)

    def _build_decision_payload(
        self,
        engine: SimulationEngine,
        veh: VehicleAgent,
        anchor: str,
        remaining: List[str],
        alt_path: List[str],
        cur_roads: List[RoadSegment],
        alt_roads: List[RoadSegment],
        cur_cost: float,
        alt_cost: float,
        saving: float,
        telemetry_completeness: float,
    ) -> Dict[str, Any]:
        avoided_roads = [r for r in cur_roads if r.road_id not in {ar.road_id for ar in alt_roads}]
        if not avoided_roads:
            avoided_roads = cur_roads

        max_density = max((r.density for r in avoided_roads), default=0.0)
        avg_density = sum(r.density for r in avoided_roads) / max(1, len(avoided_roads))
        avoided_queues = sum(r.queue_length for r in avoided_roads)
        congested_avoided = [r for r in avoided_roads if r.density >= 0.40 or r.queue_length > 0]
        avoided_levels = {r.congestion_level for r in avoided_roads}
        tolls_on_cur = sum(r.toll for r in avoided_roads)

        # Confidence reflects relative gain shrunk when network occupancy observations are sparse
        gain_ratio = min(1.0, saving / max(10.0, cur_cost))
        raw_conf = 54.0 + (gain_ratio * 28.0) + (telemetry_completeness * 15.0)
        confidence = max(48, min(97, int(round(raw_conf))))

        if saving >= 25.0 or "SEVERE" in avoided_levels or "HIGH" in avoided_levels:
            priority = "high"
        elif saving >= 12.0 or "MODERATE" in avoided_levels or avoided_queues > 0:
            priority = "medium"
        else:
            priority = "low"

        tags: List[str] = []
        if max_density >= 0.65:
            tags.append("Congestion risk")
        elif max_density >= 0.40:
            tags.append("Moderate load")
        if avoided_queues > 0:
            tags.append("Queue delay")
        if tolls_on_cur > 0:
            tags.append("Toll savings")
        if not tags:
            tags.append("Faster bypass")

        # Normalised contributions summing cleanly to 100%
        raw_density = max(0.05, avg_density * 100.0)
        raw_wait = max(0.05, saving * 1.4)
        raw_queue = max(0.05, avoided_queues * 12.0 + len(congested_avoided) * 6.0)
        raw_cap = max(0.05, max_density * 70.0)
        total_raw = raw_density + raw_wait + raw_queue + raw_cap
        vals = [
            max(1, int(round(100.0 * raw_density / total_raw))),
            max(1, int(round(100.0 * raw_wait / total_raw))),
            max(1, int(round(100.0 * raw_queue / total_raw))),
            max(1, int(round(100.0 * raw_cap / total_raw))),
        ]
        vals[0] = max(1, vals[0] + (100 - sum(vals)))
        if sum(vals) != 100:
            # Trim excess from largest factor > 1 if minimum-1 clamping pushed sum > 100
            for idx in sorted(range(4), key=lambda i: vals[i], reverse=True):
                diff = sum(vals) - 100
                if diff <= 0:
                    break
                take = min(diff, vals[idx] - 1)
                vals[idx] -= take

        factors = [
            {"label": "Traffic density", "valuePct": vals[0]},
            {"label": "Travel-time saving", "valuePct": vals[1]},
            {"label": "Queue pressure", "valuePct": vals[2]},
            {"label": "Capacity strain", "valuePct": vals[3]},
        ]

        hottest = max(avoided_roads, key=lambda r: (r.density, r.queue_length))
        via_node = alt_path[1] if len(alt_path) > 1 else veh.destination

        bullets = [
            f"Bypass saves {saving:.0f}s over current path ({cur_cost:.0f}s vs {alt_cost:.0f}s weighted cost)",
            f"Avoids {hottest.start_node} -> {hottest.end_node} at {hottest.density * 100:.0f}% occupancy ({hottest.vehicle_count}/{hottest.capacity} slots)",
            f"Skips {avoided_queues} queued vehicle(s) across {len(avoided_roads)} corridor segment(s)",
        ]

        explanation = (
            f"{veh.vehicle_id} faces heavy load on {hottest.start_node} -> {hottest.end_node} "
            f"({hottest.density * 100:.0f}% occupancy, {hottest.current_speed * 3.6:.1f} km/h). "
            f"Rerouting via {via_node} trims estimated travel delay by {saving:.0f}s."
        )

        risks: List[Dict[str, str]] = []
        for road in sorted(avoided_roads, key=lambda r: r.density, reverse=True)[:2]:
            risks.append({
                "title": f"Congestion on {road.start_node} to {road.end_node}",
                "detail": f"{road.vehicle_count}/{road.capacity} occupied ({road.density * 100:.0f}%), {road.queue_length} queued",
            })

        queue_delta = -min(avoided_queues if avoided_queues > 0 else len(congested_avoided), 12)
        energy_delta = -round(saving * ENERGY_KWH_PER_SEC_SAVED, 2)

        return {
            "id": "",
            "vehicleId": veh.vehicle_id,
            "priority": priority,
            "status": "pending",
            "confidence": confidence,
            "tick": engine.tick,
            "from": anchor,
            "to": veh.destination,
            "tags": tags[:3],
            "currentRoute": remaining,
            "suggestedRoute": alt_path,
            "estTravelSec": round(alt_cost, 1),
            "delaySavedSec": round(saving, 1),
            "explanation": explanation,
            "bullets": bullets,
            "factors": factors,
            "risks": risks,
            "impact": {
                "travelTimeSec": -round(saving, 1),
                "queueVehicles": queue_delta,
                "energyKwh": energy_delta,
            },
            "historicalSuccessPct": 88,
            "operatorNote": None,
            "_baselineTotalSec": veh.travel_time + cur_cost,
        }

    def list_decisions(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        all_items = [self._serialize_public(self._decisions[did]) for did in self._order if did in self._decisions]

        pending_items = [d for d in all_items if d["status"] == "pending"]
        approved_items = [d for d in all_items if d["status"] == "approved"]
        history_items = [d for d in all_items if d["status"] in ("approved", "rejected", "modified")]
        low_conf = sum(1 for d in pending_items if d["confidence"] < 75)

        if status_filter == "pending":
            filtered = pending_items
        elif status_filter == "approved":
            filtered = approved_items
        elif status_filter == "history":
            filtered = history_items
        else:
            filtered = all_items

        return {
            "counts": {
                "pending": len(pending_items),
                "approved": len(approved_items),
                "history": len(history_items),
                "lowConfidence": low_conf,
            },
            "items": filtered,
        }

    def get_decision(self, decision_id: str) -> Dict[str, Any]:
        dec = self._decisions.get(decision_id)
        if not dec:
            raise ApiError(404, f"Decision '{decision_id}' not found.")
        return self._serialize_public(dec)

    def _validate_custom_route(self, network: RoadNetwork, route: List[str], anchor: str, destination: str) -> List[str]:
        if len(route) < 2:
            raise ApiError(400, "Custom route must contain at least 2 intersections.")
        if route[-1] != destination:
            raise ApiError(400, f"Custom route must end at destination '{destination}'.")

        aligned = list(route)
        if aligned[0] != anchor:
            if anchor in aligned[:-1]:
                aligned = aligned[aligned.index(anchor):]
            else:
                raise ApiError(400, f"Custom route must start at current decision node '{anchor}'.")

        for i in range(len(aligned) - 1):
            if not network.get_road_between(aligned[i], aligned[i + 1]):
                raise ApiError(400, f"No road segment connects '{aligned[i]}' -> '{aligned[i + 1]}'.")
        return aligned

    def _align_suggested_route(self, network: RoadNetwork, candidate_route: List[str], anchor: str, destination: str) -> Optional[List[str]]:
        if not candidate_route or len(candidate_route) < 2 or candidate_route[-1] != destination:
            return None
        route = list(candidate_route)
        if route[0] != anchor:
            if anchor in route[:-1]:
                route = route[route.index(anchor):]
            else:
                # Re-plan from moved anchor cleanly
                _, replanned = _dijkstra_occupancy_cost(network, anchor, destination)
                if len(replanned) < 2:
                    return None
                route = replanned
        for i in range(len(route) - 1):
            if not network.get_road_between(route[i], route[i + 1]):
                return None
        return route

    def approve(self, engine: SimulationEngine, decision_id: str) -> Dict[str, Any]:
        dec = self._decisions.get(decision_id)
        if not dec:
            raise ApiError(404, f"Decision '{decision_id}' not found.")
        if dec["status"] != "pending":
            raise ApiError(409, f"Decision '{decision_id}' is already '{dec['status']}'.")

        veh = engine.fleet_manager.vehicles.get(dec["vehicleId"])
        if not veh or veh.completion_status == "COMPLETED":
            raise ApiError(409, f"Vehicle '{dec['vehicleId']}' has already completed its journey.")

        anchor, _ = _decision_anchor(veh)
        if not anchor or anchor == veh.destination:
            raise ApiError(409, f"Vehicle '{dec['vehicleId']}' is already on its final segment.")

        aligned = self._align_suggested_route(engine.network, dec["suggestedRoute"], anchor, veh.destination)
        if not aligned or not veh.update_route(aligned, reason=f"Operator approved {decision_id}", network=engine.network):
            raise ApiError(409, f"Unable to apply reroute for '{dec['vehicleId']}' in its current state.")

        dec["status"] = "approved"
        dec["suggestedRoute"] = aligned
        dec["historicalSuccessPct"] = self._historical_success_pct()
        self._cooldown_until[veh.vehicle_id] = engine.tick + COOLDOWN_TICKS

        self._stats_delay_saved += float(dec["delaySavedSec"])
        self._stats_queue_avoided += abs(int(dec["impact"]["queueVehicles"]))
        self._stats_energy_kwh += abs(float(dec["impact"]["energyKwh"]))
        self._outcomes[decision_id] = TrackedOutcome(
            decision_id=decision_id,
            vehicle_id=veh.vehicle_id,
            predicted_saving_sec=float(dec["delaySavedSec"]),
            baseline_est_total_sec=float(dec.get("_baselineTotalSec", veh.travel_time + dec["estTravelSec"] + dec["delaySavedSec"])),
        )
        self._record_activity("Approved", dec["from"], dec["to"], veh.vehicle_id, engine.tick)
        return self._serialize_public(dec)

    def reject(self, engine: SimulationEngine, decision_id: str) -> Dict[str, Any]:
        dec = self._decisions.get(decision_id)
        if not dec:
            raise ApiError(404, f"Decision '{decision_id}' not found.")
        if dec["status"] != "pending":
            raise ApiError(409, f"Decision '{decision_id}' is already '{dec['status']}'.")

        dec["status"] = "rejected"
        self._cooldown_until[dec["vehicleId"]] = engine.tick + COOLDOWN_TICKS
        self._record_activity("Rejected", dec["from"], dec["to"], dec["vehicleId"], engine.tick)
        return self._serialize_public(dec)

    def modify(
        self,
        engine: SimulationEngine,
        decision_id: str,
        note: str = "",
        route: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        dec = self._decisions.get(decision_id)
        if not dec:
            raise ApiError(404, f"Decision '{decision_id}' not found.")
        if dec["status"] != "pending":
            raise ApiError(409, f"Decision '{decision_id}' is already '{dec['status']}'.")

        veh = engine.fleet_manager.vehicles.get(dec["vehicleId"])
        if route is not None:
            if not veh or veh.completion_status == "COMPLETED":
                raise ApiError(409, f"Vehicle '{dec['vehicleId']}' has already completed its journey.")
            anchor, _ = _decision_anchor(veh)
            if not anchor:
                raise ApiError(409, f"Vehicle '{dec['vehicleId']}' cannot be rerouted now.")
            aligned = self._validate_custom_route(engine.network, route, anchor, veh.destination)
            if not veh.update_route(aligned, reason=f"Operator modified {decision_id}: {note}".strip(), network=engine.network):
                raise ApiError(409, f"Unable to apply modified route to '{dec['vehicleId']}'.")
            dec["suggestedRoute"] = aligned
            self._outcomes[decision_id] = TrackedOutcome(
                decision_id=decision_id,
                vehicle_id=veh.vehicle_id,
                predicted_saving_sec=float(dec["delaySavedSec"]),
                baseline_est_total_sec=float(dec.get("_baselineTotalSec", veh.travel_time + dec["estTravelSec"])),
            )
            self._stats_delay_saved += float(dec["delaySavedSec"]) * 0.75
            self._stats_queue_avoided += max(1, abs(int(dec["impact"]["queueVehicles"])))
            self._stats_energy_kwh += abs(float(dec["impact"]["energyKwh"])) * 0.75

        dec["status"] = "modified"
        dec["operatorNote"] = note.strip() or None
        self._cooldown_until[dec["vehicleId"]] = engine.tick + COOLDOWN_TICKS
        self._record_activity("Modified", dec["from"], dec["to"], dec["vehicleId"], engine.tick)
        return self._serialize_public(dec)

    def _record_activity(self, verb: str, from_node: str, to_node: str, vehicle_id: str, tick: int) -> None:
        self._activity.insert(0, {
            "id": f"act-{len(self._activity) + 1}-{tick}",
            "verb": verb,
            "from": from_node,
            "to": to_node,
            "at": f"Tick {tick} · {_format_utc_clock()}",
            "vehicleId": vehicle_id,
            "tick": tick,
        })
        if len(self._activity) > 40:
            self._activity = self._activity[:40]

    def get_oversight(self, engine: SimulationEngine) -> Dict[str, Any]:
        reviewed = [d for d in self._decisions.values() if d["status"] in ("approved", "modified", "rejected")]
        total_rev = len(reviewed)
        if total_rev == 0:
            approved_pct = 0
            modified_pct = 0
            rejected_pct = 0
        else:
            app_cnt = sum(1 for d in reviewed if d["status"] == "approved")
            mod_cnt = sum(1 for d in reviewed if d["status"] == "modified")
            approved_pct = int(round((app_cnt / total_rev) * 100))
            modified_pct = int(round((mod_cnt / total_rev) * 100))
            rejected_pct = max(0, 100 - approved_pct - modified_pct)

        total_queued_base = max(1, len(engine.fleet_manager.vehicles) // 2)
        queue_red_pct = min(95.0, round((self._stats_queue_avoided / total_queued_base) * 100.0, 1)) if self._stats_queue_avoided > 0 else 0.0

        return {
            "approvedPct": approved_pct,
            "modifiedPct": modified_pct,
            "rejectedPct": rejected_pct,
            "week": {
                "totalDecisions": len(self._decisions),
                "delaySavedSec": round(self._stats_delay_saved, 1),
                "queueReductionPct": queue_red_pct,
                "energySavedKwh": round(self._stats_energy_kwh, 2),
            },
        }

    def get_activity(self, limit: int = 5) -> List[Dict[str, Any]]:
        return list(self._activity[: max(1, min(limit, 40))])

    @staticmethod
    def _serialize_public(dec: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in dec.items() if not k.startswith("_")}
