"""
Vehicle Manager coordinating generation, tracking, and life-cycle of vehicle agents.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Any
import random
import pandas as pd

from agents.vehicle import VehicleAgent
from road_network.network import RoadNetwork
from routing.route_planner import RoutePlanner
from config import SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN


class VehicleManager:
    """
    Fleet manager responsible for agent instantiation, lifecycle tracking, and bulk operations.
    """
    def __init__(self, network: RoadNetwork, route_planner: RoutePlanner):
        self.network = network
        self.route_planner = route_planner
        self.vehicles: Dict[str, VehicleAgent] = {}

    def clear(self) -> None:
        """Clears all registered vehicles."""
        self.vehicles.clear()

    def add_vehicle(self, vehicle: VehicleAgent) -> None:
        """Registers a vehicle agent into the fleet."""
        self.vehicles[vehicle.vehicle_id] = vehicle

    def create_custom_vehicle(
        self,
        vehicle_id: str,
        origin: str,
        destination: str,
        driving_behaviour: str = "NORMAL",
        routing_criterion: str = "travel_time",
        include_toll: bool = False
    ) -> Optional[VehicleAgent]:
        """Creates a single user-defined vehicle."""
        if origin not in self.network.nodes or destination not in self.network.nodes:
            return None
        if origin == destination:
            return None

        route_res = self.route_planner.plan_route(
            origin, destination, "astar", routing_criterion, include_toll
        )
        if not route_res.found:
            return None

        v = VehicleAgent(
            vehicle_id=vehicle_id,
            origin=origin,
            destination=destination,
            selected_route=route_res.path,
            driving_behaviour=driving_behaviour
        )
        v.calculate_free_flow_time(self.network)
        self.add_vehicle(v)
        return v

    def generate_scenario_fleet(
        self,
        scenario_name: str,
        vehicle_count: int,
        seed: int = 42,
        routing_criterion: str = "distance",
        include_toll: bool = False,
        arrival_interval: int = 1,
        staggered_arrivals: bool = True
    ) -> List[VehicleAgent]:
        """
        Generates a synthetic fleet with reproducible random seeds tailored to specific traffic patterns,
        including staggered arrivals and rush-hour bursts.
        """
        rng = random.Random(seed)
        self.clear()
        nodes = list(self.network.nodes.keys())
        if len(nodes) < 2:
            return []

        generated: List[VehicleAgent] = []

        # Identify key functional zones in the network if present
        residential_nodes = [n for n in nodes if any(k in n for k in ["NW", "SE", "SUB", "RES", "WEST_SUB"])]
        if not residential_nodes:
            residential_nodes = nodes[:len(nodes)//2]

        commercial_nodes = [n for n in nodes if any(k in n for k in ["DT", "DOWNTOWN", "CBD", "TECH", "FIN", "EAST_CBD"])]
        if not commercial_nodes:
            commercial_nodes = nodes[len(nodes)//2:]

        for i in range(vehicle_count):
            veh_id = f"VEH_{i+1:03d}"
            
            # Select behavior distribution: 65% Normal, 20% Aggressive, 15% Cautious
            r_beh = rng.random()
            if r_beh < 0.65:
                behavior = "NORMAL"
            elif r_beh < 0.85:
                behavior = "AGGRESSIVE"
            else:
                behavior = "CAUTIOUS"

            # Assign origin and destination according to scenario
            if scenario_name == SCENARIO_LOW:
                # Dispersed, uniform random across all nodes
                orig = rng.choice(nodes)
                dest = rng.choice([n for n in nodes if n != orig])

            elif scenario_name == SCENARIO_NORMAL:
                # 60% Commute to commercial, 40% uniform random
                if rng.random() < 0.60 and commercial_nodes:
                    orig = rng.choice(residential_nodes) if residential_nodes else rng.choice(nodes)
                    valid_dests = [c for c in commercial_nodes if c != orig]
                    dest = rng.choice(valid_dests) if valid_dests else rng.choice([n for n in nodes if n != orig])
                else:
                    orig = rng.choice(nodes)
                    dest = rng.choice([n for n in nodes if n != orig])

            elif scenario_name == SCENARIO_RUSH_HOUR:
                # 85% Commute from Suburbs/Heights across into Downtown/Financial Core
                if rng.random() < 0.85 and commercial_nodes:
                    orig = rng.choice(residential_nodes) if residential_nodes else rng.choice(nodes)
                    valid_dests = [c for c in commercial_nodes if c != orig]
                    dest = rng.choice(valid_dests) if valid_dests else rng.choice([n for n in nodes if n != orig])
                else:
                    orig = rng.choice(nodes)
                    dest = rng.choice([n for n in nodes if n != orig])

            elif scenario_name == SCENARIO_UNEVEN:
                # Heavy bottleneck focusing on a single major hub (Downtown Core)
                target = "DOWNTOWN" if "DOWNTOWN" in nodes else nodes[0]
                valid_origs = [n for n in nodes if n != target]
                orig = rng.choice(valid_origs)
                dest = target

            else:
                orig = rng.choice(nodes)
                dest = rng.choice([n for n in nodes if n != orig])

            # Assign staggered departure tick
            if not staggered_arrivals or arrival_interval <= 0:
                dep_tick = 0
            elif scenario_name == SCENARIO_LOW:
                dep_tick = (i // 2) * arrival_interval
            elif scenario_name == SCENARIO_NORMAL:
                dep_tick = (i // 3) * arrival_interval
            elif scenario_name == SCENARIO_RUSH_HOUR:
                # Rush-hour traffic burst: 20% early, 65% intense peak burst, 15% tail
                r_burst = rng.random()
                if r_burst < 0.20:
                    dep_tick = rng.randint(0, max(1, 5 * arrival_interval))
                elif r_burst < 0.85:
                    dep_tick = rng.randint(5 * arrival_interval, max(6, 15 * arrival_interval))
                else:
                    dep_tick = rng.randint(15 * arrival_interval, max(16, 22 * arrival_interval))
            elif scenario_name == SCENARIO_UNEVEN:
                # Concentrated wave into bottleneck hub
                dep_tick = rng.randint(0, max(1, 12 * arrival_interval))
            else:
                dep_tick = (i // 3) * arrival_interval

            # Compute route
            route_res = self.route_planner.plan_route(
                origin=orig,
                destination=dest,
                algorithm="astar",
                criterion=routing_criterion,
                include_toll=include_toll
            )

            if route_res.found and len(route_res.path) >= 2:
                agent = VehicleAgent(
                    vehicle_id=veh_id,
                    origin=orig,
                    destination=dest,
                    selected_route=route_res.path,
                    driving_behaviour=behavior,
                    scheduled_departure_tick=dep_tick
                )
                agent.calculate_free_flow_time(self.network)
                self.add_vehicle(agent)
                generated.append(agent)

        return generated

    def step_all(self, delta_t: float = 1.0, current_tick: int = 0) -> None:
        """Advances all vehicle agents by one simulation step."""
        for vehicle in self.vehicles.values():
            vehicle.step(self.network, delta_t, current_tick)

    def get_active_vehicles(self) -> List[VehicleAgent]:
        """Vehicles currently on a road or queued."""
        return [v for v in self.vehicles.values() if v.completion_status in ("EN_ROUTE", "WAITING")]

    def get_completed_vehicles(self) -> List[VehicleAgent]:
        """Vehicles that reached their destination."""
        return [v for v in self.vehicles.values() if v.completion_status == "COMPLETED"]

    def get_unfinished_vehicles(self) -> List[VehicleAgent]:
        """Vehicles that have not yet completed their journey."""
        return [v for v in self.vehicles.values() if v.completion_status != "COMPLETED"]

    def get_waiting_vehicles(self) -> List[VehicleAgent]:
        """Vehicles currently stalled/queued due to capacity constraints."""
        return [v for v in self.vehicles.values() if v.completion_status == "WAITING"]

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Summary metrics across the entire vehicle fleet, distinguishing completed and unfinished."""
        total = len(self.vehicles)
        comp_vehicles = self.get_completed_vehicles()
        unfinished_vehicles = self.get_unfinished_vehicles()
        completed = len(comp_vehicles)
        unfinished = len(unfinished_vehicles)
        active = len(self.get_active_vehicles())
        waiting = len(self.get_waiting_vehicles())
        
        if comp_vehicles:
            avg_travel_time = sum(v.travel_time for v in comp_vehicles) / len(comp_vehicles)
            avg_delay = sum(max(0.0, v.travel_time - v.free_flow_travel_time) for v in comp_vehicles) / len(comp_vehicles)
            avg_waiting = sum(v.waiting_time for v in comp_vehicles) / len(comp_vehicles)
        else:
            avg_travel_time = 0.0
            avg_delay = 0.0
            avg_waiting = 0.0

        departed_unfinished = [v for v in unfinished_vehicles if v.travel_time > 0]
        if departed_unfinished:
            unfinished_avg_elapsed = sum(v.travel_time for v in departed_unfinished) / len(departed_unfinished)
        else:
            unfinished_avg_elapsed = 0.0

        return {
            "total_vehicles": total,
            "completed_vehicles": completed,
            "unfinished_vehicles": unfinished,
            "active_vehicles": active,
            "waiting_vehicles": waiting,
            "completion_rate": (completed / max(1, total)) * 100.0,
            "average_travel_time": round(avg_travel_time, 1),
            "unfinished_avg_elapsed": round(unfinished_avg_elapsed, 1),
            "average_delay": round(avg_delay, 1),
            "average_waiting_time": round(avg_waiting, 1)
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Converts vehicle states to a pandas DataFrame for UI table inspection."""
        if not self.vehicles:
            return pd.DataFrame()
        return pd.DataFrame([v.to_dict() for v in self.vehicles.values()])
