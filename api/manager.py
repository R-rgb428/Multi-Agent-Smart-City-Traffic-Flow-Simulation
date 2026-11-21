"""Thread-safe controller wrapping SimulationEngine and DecisionStore for FastAPI."""
from __future__ import annotations
import threading
import time
from typing import Any, Dict, List, Optional

from config import SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN
from road_network.network import RoadSegment
from simulation.engine import SimulationEngine, SimulationState
from api.decisions import ApiError, DecisionStore

VALID_SCENARIOS = {SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN}
VALID_STRATEGIES = {
    "Independent",
    "Route Advisories",
    "Congestion Pricing",
    "Dynamic Lanes",
    "Combined",
}

TOPOLOGY_ALIASES: Dict[str, tuple[str, str]] = {
    "smart_city": ("smart_city", "Metro Smart City (12 Nodes)"),
    "metro smart city": ("smart_city", "Metro Smart City (12 Nodes)"),
    "metro smart city (12 nodes)": ("smart_city", "Metro Smart City (12 Nodes)"),
    "arterial": ("arterial", "Commuter Arterial Corridor (6 Nodes)"),
    "commuter arterial corridor": ("arterial", "Commuter Arterial Corridor (6 Nodes)"),
    "commuter arterial corridor (6 nodes)": ("arterial", "Commuter Arterial Corridor (6 Nodes)"),
}

SMART_CITY_LAYOUT: Dict[str, tuple[float, float, str]] = {
    "N_GATE": (320.0, 40.0, "top"),
    "NW_RES": (124.0, 84.0, "left"),
    "NE_TECH": (516.0, 84.0, "right"),
    "RIVER_BR": (320.0, 116.0, "right"),
    "W_BYPASS": (40.0, 182.0, "bottom"),
    "W_IND": (124.0, 182.0, "bottom"),
    "DOWNTOWN": (320.0, 182.0, "bottom"),
    "E_FIN": (516.0, 182.0, "bottom"),
    "E_BYPASS": (600.0, 182.0, "bottom"),
    "SW_PORT": (124.0, 292.0, "bottom"),
    "S_CIVIC": (320.0, 292.0, "bottom"),
    "SE_SUB": (516.0, 292.0, "bottom"),
}


class SimulationManager:
    """Owns the live SimulationEngine, background tick worker thread, and DecisionStore."""

    def __init__(self, tick_interval_sec: float = 0.4) -> None:
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._tick_interval = tick_interval_sec
        self._worker_thread: Optional[threading.Thread] = None

        self.engine = SimulationEngine(network_type="smart_city", max_ticks=200)
        self.decisions = DecisionStore()
        self._topology_label = "Metro Smart City (12 Nodes)"

        self.configure(
            topology="Metro Smart City (12 Nodes)",
            scenario=SCENARIO_NORMAL,
            strategy="Independent",
            vehicles=60,
            duration_ticks=200,
            arrival_interval=1,
            seed=42,
        )

    def _start_worker_if_needed(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._run_loop, name="sim-tick-worker", daemon=True
        )
        self._worker_thread.start()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                if self.engine.state == SimulationState.RUNNING:
                    self._advance_one_tick_locked()
                    still_running = self.engine.state == SimulationState.RUNNING
                else:
                    still_running = False
            if not still_running:
                break
            self._stop_event.wait(self._tick_interval)

    def shutdown(self) -> None:
        self._stop_event.set()
        thread = self._worker_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.5)

    def _advance_one_tick_locked(self) -> None:
        if self.engine.state == SimulationState.COMPLETED:
            return
        self.engine.step()
        self.decisions.evaluate_tick(self.engine, force=False)

    def _resolve_topology(self, raw: str) -> tuple[str, str]:
        key = raw.strip().lower()
        if key not in TOPOLOGY_ALIASES:
            raise ApiError(400, f"Unknown topology '{raw}'.")
        return TOPOLOGY_ALIASES[key]

    def configure(
        self,
        topology: str,
        scenario: str,
        strategy: str,
        vehicles: int,
        duration_ticks: int,
        arrival_interval: int,
        seed: int,
    ) -> Dict[str, Any]:
        net_type, topo_label = self._resolve_topology(topology)
        if scenario not in VALID_SCENARIOS:
            raise ApiError(400, f"Unknown scenario '{scenario}'.")
        if strategy not in VALID_STRATEGIES:
            raise ApiError(400, f"Unknown strategy '{strategy}'.")

        with self._lock:
            self._stop_event.set()
            self.engine.max_ticks = duration_ticks
            self.engine.setup(
                scenario_name=scenario,
                vehicle_count=vehicles,
                strategy_name=strategy,
                seed=seed,
                network_type=net_type,
                arrival_interval=arrival_interval,
            )
            self._topology_label = topo_label
            self.decisions.reset()
            return self.get_state()

    def start(self) -> Dict[str, Any]:
        with self._lock:
            if self.engine.state == SimulationState.COMPLETED:
                raise ApiError(409, "Simulation has already finished. Reset or configure before starting.")
            self.engine.start()
            self._start_worker_if_needed()
            return self.get_state()

    def pause(self) -> Dict[str, Any]:
        with self._lock:
            self.engine.pause()
            return self.get_state()

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._stop_event.set()
            self.engine.reset()
            self.decisions.reset()
            return self.get_state()

    def step(self, ticks: int = 1) -> Dict[str, Any]:
        if ticks < 1 or ticks > 50:
            raise ApiError(400, "ticks must be between 1 and 50.")
        with self._lock:
            if self.engine.state == SimulationState.COMPLETED:
                raise ApiError(409, "Simulation has already finished.")
            prev_state = self.engine.state
            for _ in range(ticks):
                if self.engine.state == SimulationState.COMPLETED:
                    break
                if self.engine.state == SimulationState.IDLE:
                    self.engine.state = SimulationState.READY
                self._advance_one_tick_locked()
            if prev_state == SimulationState.READY and self.engine.state == SimulationState.READY:
                self.engine.state = SimulationState.PAUSED
            # Ensure interactive stepping can still surface decisions promptly once congestion appears
            self.decisions.evaluate_tick(self.engine, force=True)
            return self.get_state()

    def _map_status(self, state: SimulationState) -> str:
        if state in (SimulationState.IDLE, SimulationState.READY):
            return "ready"
        if state == SimulationState.RUNNING:
            return "running"
        if state == SimulationState.PAUSED:
            return "paused"
        return "finished"

    def _project_nodes(self) -> List[Dict[str, Any]]:
        nodes = list(self.engine.network.nodes.values())
        if not nodes:
            return []

        if self.engine.network_type == "smart_city":
            out = []
            for n in nodes:
                x, y, label_at = SMART_CITY_LAYOUT.get(n.node_id, (320.0, 170.0, "bottom"))
                out.append({
                    "id": n.node_id,
                    "label": n.name,
                    "x": x,
                    "y": y,
                    "labelAt": label_at,
                })
            return out

        xs = [n.x for n in nodes]
        ys = [n.y for n in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)

        out = []
        for n in nodes:
            px = 64.0 + ((n.x - min_x) / span_x) * (640.0 - 128.0)
            # Invert Y so larger meters Y sits higher on canvas
            py = 60.0 + ((max_y - n.y) / span_y) * (340.0 - 140.0)
            out.append({
                "id": n.node_id,
                "label": n.name,
                "x": round(px, 1),
                "y": round(py, 1),
                "labelAt": "top" if py < 120 else "bottom",
            })
        return out

    @staticmethod
    def _road_level(road: RoadSegment) -> str:
        if road.vehicle_count == 0 and road.queue_length == 0:
            return "idle"
        return road.congestion_level.lower()

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            fleet = self.engine.fleet_manager.get_fleet_summary()
            net = self.engine.network.get_network_summary()

            dist = {"idle": 0, "low": 0, "moderate": 0, "high": 0, "severe": 0}
            roads_out: List[Dict[str, Any]] = []
            for road in self.engine.network.roads.values():
                level = self._road_level(road)
                dist[level] += 1
                roads_out.append({
                    "id": f"{road.start_node}>{road.end_node}",
                    "from": road.start_node,
                    "to": road.end_node,
                    "level": level,
                    "occupancyPct": round(road.density * 100.0, 1),
                    "vehicles": road.vehicle_count,
                    "capacity": road.capacity,
                    "lanes": road.current_lanes,
                    "speedKmh": round(road.current_speed * 3.6, 1),
                    "toll": round(road.toll, 2),
                    "queue": road.queue_length,
                })

            vehicles_out: List[Dict[str, Any]] = []
            for v in self.engine.fleet_manager.vehicles.values():
                if v.completion_status == "EN_ROUTE" and v.current_road_id:
                    road_obj = self.engine.network.get_road(v.current_road_id)
                    if not road_obj:
                        continue
                    vehicles_out.append({
                        "id": v.vehicle_id,
                        "road": f"{road_obj.start_node}>{road_obj.end_node}",
                        "progress": round(v.progress_ratio, 3),
                        "state": "moving",
                        "fromNode": road_obj.start_node,
                        "toNode": road_obj.end_node,
                        "speedKmh": round(v.current_speed * 3.6, 1),
                        "behaviour": v.driving_behaviour,
                        "delaySec": round(max(0.0, v.travel_time - v.free_flow_travel_time), 1),
                    })
                elif v.completion_status == "WAITING" and v.target_node:
                    vehicles_out.append({
                        "id": v.vehicle_id,
                        "road": f"{v.current_node}>{v.target_node}",
                        "progress": 0.0,
                        "state": "queued",
                        "fromNode": v.current_node,
                        "toNode": v.target_node,
                        "speedKmh": 0.0,
                        "behaviour": v.driving_behaviour,
                        "delaySec": round(max(0.0, v.travel_time - v.free_flow_travel_time), 1),
                    })

            return {
                "status": self._map_status(self.engine.state),
                "tick": self.engine.tick,
                "maxTicks": self.engine.max_ticks,
                "scenario": self.engine.scenario_name,
                "strategy": self.engine.strategy_name,
                "topology": self._topology_label,
                "seed": self.engine.seed,
                "arrivalInterval": self.engine.arrival_interval,
                "kpis": {
                    "totalVehicles": fleet["total_vehicles"],
                    "activeVehicles": fleet["active_vehicles"],
                    "queuedAtIntersections": net["total_queued"],
                    "completedJourneys": fleet["completed_vehicles"],
                    "completionRatePct": round(fleet["completion_rate"], 1),
                    "avgTravelTimeSec": fleet["average_travel_time"],
                    "avgDelaySec": fleet["average_delay"],
                    "networkCongestionPct": round(net["average_density"] * 100.0, 1),
                    "occupiedSlots": net["total_vehicles"],
                    "totalSlots": net["total_capacity"],
                },
                "nodes": self._project_nodes(),
                "roads": roads_out,
                "congestionDistribution": dist,
                "vehicles": vehicles_out,
            }

    def list_decisions(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            return self.decisions.list_decisions(status_filter)

    def get_decision(self, decision_id: str) -> Dict[str, Any]:
        with self._lock:
            return self.decisions.get_decision(decision_id)

    def approve_decision(self, decision_id: str) -> Dict[str, Any]:
        with self._lock:
            return self.decisions.approve(self.engine, decision_id)

    def reject_decision(self, decision_id: str) -> Dict[str, Any]:
        with self._lock:
            return self.decisions.reject(self.engine, decision_id)

    def modify_decision(self, decision_id: str, note: str, route: Optional[List[str]]) -> Dict[str, Any]:
        with self._lock:
            return self.decisions.modify(self.engine, decision_id, note=note, route=route)

    def get_oversight(self) -> Dict[str, Any]:
        with self._lock:
            return self.decisions.get_oversight(self.engine)

    def get_activity(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._lock:
            return self.decisions.get_activity(limit=limit)

    def get_fleet_vehicles(self) -> List[Dict[str, Any]]:
        with self._lock:
            out: List[Dict[str, Any]] = []
            for v in self.engine.fleet_manager.vehicles.values():
                road_str = None
                if v.current_road_id:
                    road_obj = self.engine.network.get_road(v.current_road_id)
                    if road_obj:
                        road_str = f"{road_obj.start_node}>{road_obj.end_node}"
                out.append({
                    "id": v.vehicle_id,
                    "origin": v.origin,
                    "destination": v.destination,
                    "currentNode": v.current_node,
                    "targetNode": v.target_node,
                    "road": road_str,
                    "route": list(v.selected_route),
                    "behaviour": v.driving_behaviour,
                    "status": v.completion_status,
                    "speedKmh": round(v.current_speed * 3.6, 1),
                    "travelTimeSec": round(v.travel_time, 1),
                    "waitingTimeSec": round(v.waiting_time, 1),
                    "delaySec": round(max(0.0, v.travel_time - v.free_flow_travel_time), 1),
                    "tollPaid": round(v.toll_paid, 2),
                    "reroutes": v.reroute_count,
                    "scheduledTick": v.scheduled_departure_tick,
                })
            return out

    def get_telemetry(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "tick": snap.tick,
                    "activeVehicles": snap.active_vehicles,
                    "completedVehicles": snap.completed_vehicles,
                    "queuedVehicles": snap.queued_vehicles,
                    "avgSpeedKmh": round(snap.average_speed_kmh, 1),
                    "avgDensityPct": round(snap.average_density * 100.0, 2),
                    "totalSystemDelay": round(snap.total_system_delay, 1),
                }
                for snap in self.engine.monitor.history
            ]
