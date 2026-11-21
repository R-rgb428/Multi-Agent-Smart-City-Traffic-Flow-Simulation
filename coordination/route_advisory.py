"""
Route Advisory Coordination Mechanism.
Identifies bottlenecks, calculates alternative routes, and advises vehicle agents.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import pandas as pd

from road_network.network import RoadNetwork
from agents.vehicle import VehicleAgent
from routing.route_planner import RoutePlanner


@dataclass
class AdvisoryEvent:
    """Log record of a route advisory decision."""
    tick: int
    vehicle_id: str
    current_node: str
    destination: str
    congested_road: str
    old_route: str
    new_route: str
    time_saved_sec: float
    reason: str
    accepted: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "vehicle_id": self.vehicle_id,
            "current_node": self.current_node,
            "destination": self.destination,
            "congested_road": self.congested_road,
            "old_route": self.old_route,
            "new_route": self.new_route,
            "time_saved_sec": round(self.time_saved_sec, 1),
            "reason": self.reason,
            "accepted": "Accepted" if self.accepted else "Declined (Inertia)"
        }


class RouteAdvisorySystem:
    """
    Intelligent Advisory service detecting congestion and broadcasting reroute advice.
    """
    def __init__(
        self,
        density_threshold: float = 0.70,
        switch_cost_penalty: float = 12.0,  # seconds inertia barrier
        cooldown_ticks: int = 8
    ):
        self.density_threshold = density_threshold
        self.switch_cost_penalty = switch_cost_penalty
        self.cooldown_ticks = cooldown_ticks
        self.events: List[AdvisoryEvent] = []
        self._last_advisory_tick: Dict[str, int] = {}

    def reset(self) -> None:
        self.events.clear()
        self._last_advisory_tick.clear()

    def evaluate_and_advise(
        self,
        tick: int,
        network: RoadNetwork,
        vehicles: List[VehicleAgent],
        planner: RoutePlanner,
        include_toll: bool = False
    ) -> List[AdvisoryEvent]:
        """
        Evaluates active vehicles and issues advisories where congestion can be alleviated.
        """
        new_events: List[AdvisoryEvent] = []

        # 1. Identify all congested road segments
        congested_road_ids = {
            r_id for r_id, road in network.roads.items()
            if road.density >= self.density_threshold
        }

        if not congested_road_ids:
            return new_events

        # 2. Iterate through vehicles currently en route or waiting at intersections
        for v in vehicles:
            if v.completion_status not in ("EN_ROUTE", "WAITING"):
                continue

            # Respect cooldown to prevent route oscillation / flapping
            if (tick - self._last_advisory_tick.get(v.vehicle_id, -999)) < self.cooldown_ticks:
                continue

            # Determine decision node: EN_ROUTE vehicles can only divert from target_node
            if v.completion_status == "EN_ROUTE" and v.target_node:
                decision_node = v.target_node
                start_idx = v.route_index + 1
            else:
                decision_node = v.current_node
                start_idx = v.route_index

            if decision_node == v.destination:
                continue

            # Check if any road in vehicle's remaining path from decision_node is congested
            remaining_nodes = v.selected_route[start_idx:]
            if len(remaining_nodes) < 2:
                continue

            troubled_road: Optional[str] = None
            current_remaining_time = 0.0

            for i in range(len(remaining_nodes) - 1):
                u, nxt = remaining_nodes[i], remaining_nodes[i + 1]
                road = network.get_road_between(u, nxt)
                if road:
                    current_remaining_time += road.estimated_travel_time
                    if road.road_id in congested_road_ids and troubled_road is None:
                        troubled_road = road.road_id

            if not troubled_road:
                continue  # Remaining route is clear!

            # 3. Calculate candidate alternative route from decision_node to destination
            alt_res = planner.plan_route(
                origin=decision_node,
                destination=v.destination,
                algorithm="astar",
                criterion="travel_time",
                include_toll=include_toll
            )

            if not alt_res.found or len(alt_res.path) < 2:
                continue

            # Check if the proposed alternative is actually different
            if alt_res.path == remaining_nodes:
                continue

            time_saved = current_remaining_time - alt_res.estimated_travel_time

            # 4. Agent decision rule accounting for driver behavior and switching costs
            sensitivity = v.behavior_params["reroute_sensitivity"]
            # Effective inertia threshold: aggressive drivers switch more easily
            effective_threshold = self.switch_cost_penalty * (1.2 - sensitivity)

            accepted = time_saved > effective_threshold

            if accepted:
                reason = (
                    f"Bottleneck on road {troubled_road} (Density: {network.get_road(troubled_road).density*100:.0f}%). "
                    f"Rerouting from {decision_node} via {alt_res.path[1]} saves ~{time_saved:.1f}s."
                )
                v.update_route(alt_res.path, reason=reason, network=network)
                self._last_advisory_tick[v.vehicle_id] = tick
            else:
                reason = (
                    f"Congestion on {troubled_road}, but alternative saves only {time_saved:.1f}s, "
                    f"which is below switching inertia threshold ({effective_threshold:.1f}s)."
                )

            event = AdvisoryEvent(
                tick=tick,
                vehicle_id=v.vehicle_id,
                current_node=decision_node,
                destination=v.destination,
                congested_road=troubled_road,
                old_route=" -> ".join(remaining_nodes),
                new_route=" -> ".join(alt_res.path),
                time_saved_sec=time_saved,
                reason=reason,
                accepted=accepted
            )
            self.events.append(event)
            new_events.append(event)

        return new_events

    def to_dataframe(self) -> pd.DataFrame:
        """Returns log of advisories as a DataFrame."""
        if not self.events:
            return pd.DataFrame()
        return pd.DataFrame([e.to_dict() for e in self.events])
