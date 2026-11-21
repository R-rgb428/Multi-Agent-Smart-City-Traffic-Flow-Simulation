"""
Vehicle Agent Model representing an autonomous vehicle in an urban network.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import random

from config import DRIVER_BEHAVIORS
from road_network.network import RoadNetwork, RoadSegment


@dataclass
class VehicleAgent:
    """
    Autonomous Vehicle Agent that navigates the road network.
    """
    vehicle_id: str
    origin: str
    destination: str
    selected_route: List[str]               # Node sequence [origin, ..., destination]
    driving_behaviour: str = "NORMAL"       # "NORMAL", "AGGRESSIVE", "CAUTIOUS"
    
    # State tracking
    current_node: str = ""
    target_node: Optional[str] = None
    current_road_id: Optional[str] = None
    current_road_length: float = 1.0        # Length of current road segment (meters)
    route_index: int = 0                    # Index of current_node in selected_route
    progress_distance: float = 0.0          # Meters traversed on current road
    current_speed: float = 0.0              # Current speed in m/s
    completion_status: str = "PENDING"      # "PENDING", "EN_ROUTE", "WAITING", "COMPLETED"
    
    # Performance metrics
    travel_time: float = 0.0                # Total simulation seconds spent
    waiting_time: float = 0.0               # Seconds delayed/queued
    free_flow_travel_time: float = 0.0      # Baseline minimum theoretical time
    toll_paid: float = 0.0                  # Total virtual congestion tolls paid
    reroute_count: int = 0                  # Number of rerouting adjustments
    
    scheduled_departure_tick: int = 0
    entry_tick: int = 0
    completion_tick: Optional[int] = None
    
    def __post_init__(self):
        if not self.current_node:
            self.current_node = self.origin
        if self.driving_behaviour not in DRIVER_BEHAVIORS:
            self.driving_behaviour = "NORMAL"

    @property
    def behavior_params(self) -> Dict[str, float]:
        return DRIVER_BEHAVIORS.get(self.driving_behaviour, DRIVER_BEHAVIORS["NORMAL"])

    @property
    def progress_ratio(self) -> float:
        """Percentage completion of current road segment (0.0 to 1.0)."""
        if self.completion_status == "COMPLETED":
            return 1.0
        if not self.current_road_id:
            return 0.0
        return min(1.0, max(0.0, self.progress_distance / max(1.0, self.current_road_length)))

    def calculate_free_flow_time(self, network: RoadNetwork) -> float:
        """Calculates total ideal free flow time for current selected route."""
        total = 0.0
        for i in range(len(self.selected_route) - 1):
            road = network.get_road_between(self.selected_route[i], self.selected_route[i + 1])
            if road:
                total += road.free_flow_time
        self.free_flow_travel_time = total
        return total

    def step(self, network: RoadNetwork, delta_t: float = 1.0, current_tick: int = 0) -> None:
        """
        Executes a single simulation step for this vehicle agent.
        Respects road capacities, queues at intersections, and calculates realistic progression.
        """
        if self.completion_status == "COMPLETED":
            return

        # Case 1: Vehicle is PENDING at origin (respect staggered departure schedule)
        if self.completion_status == "PENDING":
            if current_tick < self.scheduled_departure_tick:
                return
            if len(self.selected_route) < 2:
                self.completion_status = "COMPLETED"
                self.completion_tick = current_tick
                return

            first_u = self.selected_route[0]
            first_v = self.selected_route[1]
            first_road = network.get_road_between(first_u, first_v)

            if not first_road:
                # Road does not exist
                self.completion_status = "COMPLETED"
                return

            if first_road.can_accommodate():
                # Successfully entered the network
                first_road.add_vehicle(self.vehicle_id)
                self.current_road_id = first_road.road_id
                self.current_road_length = first_road.length
                self.current_node = first_u
                self.target_node = first_v
                self.route_index = 0
                self.progress_distance = 0.0
                self.current_speed = first_road.current_speed * self.behavior_params["speed_factor"]
                self.completion_status = "EN_ROUTE"
                self.entry_tick = current_tick
            else:
                # Queued at origin waiting for capacity
                first_road.add_to_queue(self.vehicle_id)
                self.target_node = first_v
                self.completion_status = "WAITING"
                self.travel_time += delta_t
                self.waiting_time += delta_t
            return

        # Case 2: Vehicle is WAITING in queue (at origin or at intersection)
        if self.completion_status == "WAITING":
            self.travel_time += delta_t
            self.waiting_time += delta_t

            # Target road vehicle is attempting to enter
            if self.route_index + 1 < len(self.selected_route):
                next_node = self.selected_route[self.route_index + 1]
                target_road = network.get_road_between(self.current_node, next_node)
                
                is_front_of_queue = (
                    not target_road.queue
                    or target_road.queue[0] == self.vehicle_id
                    or self.vehicle_id not in target_road.queue
                ) if target_road else False

                if target_road and target_road.can_accommodate() and is_front_of_queue:
                    # Capacity is now available!
                    target_road.remove_from_queue(self.vehicle_id)
                    target_road.add_vehicle(self.vehicle_id)
                    
                    if target_road.toll > 0:
                        self.toll_paid += target_road.toll

                    self.current_road_id = target_road.road_id
                    self.current_road_length = target_road.length
                    self.target_node = next_node
                    self.progress_distance = 0.0
                    self.current_speed = target_road.current_speed * self.behavior_params["speed_factor"]
                    self.completion_status = "EN_ROUTE"
            return

        # Case 3: Vehicle is EN_ROUTE on current road
        if self.completion_status == "EN_ROUTE":
            self.travel_time += delta_t
            road = network.get_road(self.current_road_id) if self.current_road_id else None

            if not road:
                self.completion_status = "COMPLETED"
                self.completion_tick = current_tick
                return

            # Dynamic speed adjusted by congestion and driver behavior
            effective_speed = road.current_speed * self.behavior_params["speed_factor"]
            self.current_speed = effective_speed
            self.progress_distance += effective_speed * delta_t

            # Has vehicle reached the end of this road segment?
            if self.progress_distance >= road.length:
                # Arrived at road.end_node
                arrived_node = road.end_node
                self.current_node = arrived_node

                if arrived_node == self.destination or self.route_index + 1 >= len(self.selected_route):
                    # Destination reached!
                    road.remove_vehicle(self.vehicle_id)
                    self.current_road_id = None
                    self.target_node = None
                    self.completion_status = "COMPLETED"
                    self.completion_tick = current_tick
                    return
                else:
                    # Vehicle wants to proceed to next road segment
                    next_node = self.selected_route[self.route_index + 2] if (self.route_index + 2 < len(self.selected_route)) else None
                    if not next_node:
                        # Reached destination node of the path
                        road.remove_vehicle(self.vehicle_id)
                        self.current_road_id = None
                        self.target_node = None
                        self.completion_status = "COMPLETED"
                        self.completion_tick = current_tick
                        return

                    next_road = network.get_road_between(arrived_node, next_node)
                    if not next_road:
                        road.remove_vehicle(self.vehicle_id)
                        self.completion_status = "COMPLETED"
                        self.completion_tick = current_tick
                        return

                    if next_road.can_accommodate():
                        # Seamless transition into next road segment
                        road.remove_vehicle(self.vehicle_id)
                        next_road.add_vehicle(self.vehicle_id)
                        
                        if next_road.toll > 0:
                            self.toll_paid += next_road.toll
                            
                        self.current_road_id = next_road.road_id
                        self.current_road_length = next_road.length
                        self.target_node = next_node
                        self.route_index += 1
                        self.progress_distance = 0.0
                        self.current_speed = next_road.current_speed * self.behavior_params["speed_factor"]
                    else:
                        # Next road is congested and full! Vehicle must queue at intersection
                        road.remove_vehicle(self.vehicle_id)
                        next_road.add_to_queue(self.vehicle_id)
                        self.current_road_id = None
                        self.route_index += 1
                        self.target_node = next_node
                        self.completion_status = "WAITING"
                        self.waiting_time += delta_t

    def update_route(
        self,
        new_route: List[str],
        reason: str = "",
        network: Optional[RoadNetwork] = None
    ) -> bool:
        """
        Updates the vehicle's remaining route to its destination.
        - If EN_ROUTE on current_road, new_route must begin at target_node (end of current road).
        - If WAITING or PENDING at current_node, new_route must begin at current_node.
        """
        if not new_route or len(new_route) < 2 or new_route[-1] != self.destination:
            return False

        if self.completion_status == "EN_ROUTE":
            if not self.target_node or new_route[0] != self.target_node:
                return False
            past_path = self.selected_route[:self.route_index + 1]
            self.selected_route = past_path + new_route
            self.reroute_count += 1
            return True

        elif self.completion_status in ("WAITING", "PENDING"):
            if new_route[0] != self.current_node:
                return False
            # Clean up old queue entry if switching away from previously queued road
            if network and self.completion_status == "WAITING" and self.route_index + 1 < len(self.selected_route):
                old_next = self.selected_route[self.route_index + 1]
                if old_next != new_route[1]:
                    old_road = network.get_road_between(self.current_node, old_next)
                    if old_road:
                        old_road.remove_from_queue(self.vehicle_id)
                    new_road = network.get_road_between(self.current_node, new_route[1])
                    if new_road and not new_road.can_accommodate():
                        new_road.add_to_queue(self.vehicle_id)

            past_path = self.selected_route[:self.route_index]
            self.selected_route = past_path + new_route
            self.route_index = len(past_path)
            self.target_node = new_route[1]
            self.reroute_count += 1
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "origin": self.origin,
            "destination": self.destination,
            "current_node": self.current_node,
            "target_node": self.target_node,
            "current_road_id": self.current_road_id,
            "route": " -> ".join(self.selected_route),
            "driving_behaviour": self.driving_behaviour,
            "status": self.completion_status,
            "current_speed": round(self.current_speed * 3.6, 1),  # convert to km/h for UI
            "travel_time": round(self.travel_time, 1),
            "waiting_time": round(self.waiting_time, 1),
            "free_flow_time": round(self.free_flow_travel_time, 1),
            "delay": round(max(0.0, self.travel_time - self.free_flow_travel_time), 1),
            "toll_paid": round(self.toll_paid, 2),
            "reroutes": self.reroute_count,
            "scheduled_tick": self.scheduled_departure_tick
        }
