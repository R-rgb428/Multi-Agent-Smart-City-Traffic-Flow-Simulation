"""
Unified AI Coordinator managing multi-agent traffic coordination strategies.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import pandas as pd

from road_network.network import RoadNetwork
from agents.vehicle import VehicleAgent
from agents.vehicle_manager import VehicleManager
from routing.route_planner import RoutePlanner
from monitoring.traffic_monitor import TrafficMonitor
from coordination.route_advisory import RouteAdvisorySystem, AdvisoryEvent
from coordination.congestion_pricing import CongestionPricingSystem, PricingEvent
from coordination.dynamic_lane import DynamicLaneAssignmentSystem, LaneAdjustmentEvent
from config import CoordinationConfig


class AICoordinator:
    """
    Central AI Traffic Management Center implementing and orchestrating all three coordination mechanisms.
    """
    def __init__(self, config: Optional[CoordinationConfig] = None):
        self.config = config or CoordinationConfig()
        
        self.advisory_system = RouteAdvisorySystem(
            density_threshold=self.config.advisory_density_threshold,
            switch_cost_penalty=self.config.advisory_switch_cost_penalty
        )
        self.pricing_system = CongestionPricingSystem(
            density_threshold=self.config.pricing_density_threshold,
            base_multiplier=self.config.pricing_multiplier
        )
        self.lane_system = DynamicLaneAssignmentSystem(
            ratio_threshold=self.config.dynamic_lane_ratio_threshold,
            rebalance_interval=self.config.lane_rebalance_interval
        )
        
        self.active_strategy_name: str = "Independent"
        self.decision_log: List[Dict[str, Any]] = []
        self._last_pricing_reroute_tick: Dict[str, int] = {}

    def set_strategy(self, strategy_name: str) -> None:
        """
        Configures active coordination sub-modules based on strategy preset:
        - 'Independent' (Baseline, all off)
        - 'Route Advisories'
        - 'Congestion Pricing'
        - 'Dynamic Lanes'
        - 'Combined' (All on)
        """
        self.active_strategy_name = strategy_name
        if strategy_name == "Independent":
            self.config.enable_advisories = False
            self.config.enable_pricing = False
            self.config.enable_dynamic_lanes = False
        elif strategy_name == "Route Advisories":
            self.config.enable_advisories = True
            self.config.enable_pricing = False
            self.config.enable_dynamic_lanes = False
        elif strategy_name == "Congestion Pricing":
            self.config.enable_advisories = False
            self.config.enable_pricing = True
            self.config.enable_dynamic_lanes = False
        elif strategy_name == "Dynamic Lanes":
            self.config.enable_advisories = False
            self.config.enable_pricing = False
            self.config.enable_dynamic_lanes = True
        elif strategy_name == "Combined":
            self.config.enable_advisories = True
            self.config.enable_pricing = True
            self.config.enable_dynamic_lanes = True

    def reset(self) -> None:
        """Resets all sub-modules and decision logs."""
        self.advisory_system.reset()
        self.pricing_system.reset()
        self.lane_system.reset()
        self.decision_log.clear()
        self._last_pricing_reroute_tick.clear()

    def _apply_pricing_response(
        self,
        tick: int,
        network: RoadNetwork,
        fleet_manager: VehicleManager,
        planner: RoutePlanner
    ) -> int:
        """
        Models economic agent response to congestion pricing tolls.
        Vehicles facing tolled roads ahead evaluate toll-adjusted generalized cost
        and divert to lower-cost bypasses if savings exceed switching threshold.
        """
        tolled_roads = {r_id for r_id, r in network.roads.items() if r.toll > 0}
        if not tolled_roads:
            return 0

        reroutes = 0
        candidates = [
            v for v in fleet_manager.vehicles.values()
            if v.completion_status in ("EN_ROUTE", "WAITING")
            or (v.completion_status == "PENDING" and tick >= v.scheduled_departure_tick)
        ]
        for v in candidates:
            if (tick - self._last_pricing_reroute_tick.get(v.vehicle_id, -999)) < 8:
                continue

            if v.completion_status == "EN_ROUTE" and v.target_node:
                decision_node = v.target_node
                start_idx = v.route_index + 1
            else:
                decision_node = v.current_node
                start_idx = v.route_index

            if decision_node == v.destination:
                continue

            remaining_nodes = v.selected_route[start_idx:]
            if len(remaining_nodes) < 2:
                continue

            price_sens = v.behavior_params["price_sensitivity"]
            current_gen_cost = 0.0
            has_toll_ahead = False

            for i in range(len(remaining_nodes) - 1):
                road = network.get_road_between(remaining_nodes[i], remaining_nodes[i + 1])
                if road:
                    if road.toll > 0:
                        has_toll_ahead = True
                    current_gen_cost += road.estimated_travel_time + (road.toll * price_sens)

            if not has_toll_ahead:
                continue

            alt_res = planner.plan_route(
                origin=decision_node,
                destination=v.destination,
                algorithm="astar",
                criterion="travel_time",
                include_toll=True,
                toll_sensitivity=price_sens
            )

            if not alt_res.found or len(alt_res.path) < 2 or alt_res.path == remaining_nodes:
                continue

            new_gen_cost = alt_res.estimated_travel_time + (alt_res.total_toll * price_sens)
            if (current_gen_cost - new_gen_cost) > 6.0:
                reason = (
                    f"Pricing signal on tolled corridor ahead. Diverting from {decision_node} "
                    f"via {alt_res.path[1]} reduces generalized cost by {current_gen_cost - new_gen_cost:.1f}."
                )
                if v.update_route(alt_res.path, reason=reason, network=network):
                    self._last_pricing_reroute_tick[v.vehicle_id] = tick
                    reroutes += 1
                    self.decision_log.append({
                        "tick": tick,
                        "mechanism": "Congestion Pricing",
                        "target": v.vehicle_id,
                        "action": f"Toll Avoidance Reroute",
                        "explanation": reason
                    })

        return reroutes

    def step(
        self,
        tick: int,
        network: RoadNetwork,
        fleet_manager: VehicleManager,
        monitor: TrafficMonitor,
        planner: RoutePlanner
    ) -> Dict[str, Any]:
        """
        Executes one coordinated decision cycle across the network:
        1. Dynamic Lane Assignment (physical capacity rebalancing)
        2. Congestion Pricing (economic price signals + agent toll response)
        3. Route Advisories (agent navigation guidance)
        """
        results = {
            "tick": tick,
            "lane_events": [],
            "pricing_events": [],
            "advisory_events": [],
            "pricing_reroutes": 0
        }

        # Step 1: Dynamic Lane Assignment
        if self.config.enable_dynamic_lanes:
            lane_events = self.lane_system.evaluate_and_reallocate(tick, network)
            results["lane_events"] = lane_events
            for le in lane_events:
                self.decision_log.append({
                    "tick": tick,
                    "mechanism": "Dynamic Lanes",
                    "target": le.corridor,
                    "action": le.action,
                    "explanation": le.reason
                })

        # Step 2: Congestion Pricing
        if self.config.enable_pricing:
            pricing_events = self.pricing_system.update_tolls(tick, network)
            results["pricing_events"] = pricing_events
            for pe in pricing_events:
                self.decision_log.append({
                    "tick": tick,
                    "mechanism": "Congestion Pricing",
                    "target": pe.corridor,
                    "action": f"Toll {pe.new_toll}",
                    "explanation": pe.reason
                })
        else:
            # Ensure tolls are zero if pricing disabled
            for road in network.roads.values():
                road.toll = 0.0

        # Step 3: Update Graph Weights for Routing
        network.update_graph_weights(
            cost_type="congestion_aware" if self.config.enable_pricing or self.config.enable_advisories else "travel_time",
            include_toll=self.config.enable_pricing
        )

        # Step 4: Route Advisories
        if self.config.enable_advisories:
            active_vehicles = fleet_manager.get_active_vehicles()
            advisory_events = self.advisory_system.evaluate_and_advise(
                tick, network, active_vehicles, planner,
                include_toll=self.config.enable_pricing
            )
            results["advisory_events"] = advisory_events
            for ae in advisory_events:
                if ae.accepted:
                    self.decision_log.append({
                        "tick": tick,
                        "mechanism": "Route Advisory",
                        "target": ae.vehicle_id,
                        "action": f"Rerouted to bypass {ae.congested_road}",
                        "explanation": ae.reason
                    })

        # Step 5: Economic response to Congestion Pricing (even when Advisories are off)
        if self.config.enable_pricing:
            results["pricing_reroutes"] = self._apply_pricing_response(
                tick, network, fleet_manager, planner
            )

        return results

    def get_decision_log_dataframe(self) -> pd.DataFrame:
        """Returns unified decision logs formatted as DataFrame."""
        if not self.decision_log:
            return pd.DataFrame()
        return pd.DataFrame(self.decision_log)
