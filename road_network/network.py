"""
Road Network implementation using NetworkX for Smart City Traffic Flow Simulation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import math
import networkx as nx

from config import CONGESTION_LEVELS


@dataclass
class Intersection:
    """Represents an intersection (node in the road network graph)."""
    node_id: str
    name: str
    x: float
    y: float
    connected_roads: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "connected_roads": list(self.connected_roads)
        }


@dataclass
class RoadSegment:
    """
    Represents a directed road connecting start_node to end_node.
    """
    road_id: str
    start_node: str
    end_node: str
    length: float                     # meters
    free_flow_speed: float            # meters / second (e.g., 13.89 m/s = 50 km/h)
    base_lanes: int = 2
    current_lanes: int = 2
    capacity_per_lane: int = 6        # Max vehicles per lane on this segment
    paired_road_id: Optional[str] = None  # Counter-directional road segment ID for dynamic lane assignment
    
    # Dynamic state
    vehicles: List[str] = field(default_factory=list)       # Vehicle IDs currently on road
    queue: List[str] = field(default_factory=list)          # Vehicles queued to enter this road
    toll: float = 0.0                                       # Virtual congestion toll (Pricing mechanism)
    
    @property
    def capacity(self) -> int:
        """Total maximum simultaneous vehicle capacity."""
        return max(1, self.current_lanes * self.capacity_per_lane)

    @property
    def vehicle_count(self) -> int:
        """Current number of vehicles traveling on this segment."""
        return len(self.vehicles)

    @property
    def queue_length(self) -> int:
        """Current number of vehicles waiting in queue to enter."""
        return len(self.queue)

    @property
    def density(self) -> float:
        """Traffic density: ratio of current vehicles to capacity (0.0 to 1.0+)."""
        return self.vehicle_count / float(self.capacity)

    @property
    def current_speed(self) -> float:
        """
        Speed based on Greenshields / BPR non-linear speed-density relationship.
        Speed degrades as density increases, maintaining a minimum crawl speed (15% of free flow).
        """
        d = min(1.0, self.density)
        # Smooth polynomial reduction: v = v0 * (1 - 0.85 * d^2)
        degradation = 0.85 * (d ** 2)
        speed = self.free_flow_speed * max(0.15, 1.0 - degradation)
        return speed

    @property
    def free_flow_time(self) -> float:
        """Theoretical minimum travel time under zero traffic (seconds)."""
        return self.length / max(1.0, self.free_flow_speed)

    @property
    def estimated_travel_time(self) -> float:
        """
        Current estimated travel time in seconds, accounting for congestion speed and queuing delay.
        """
        traversal_time = self.length / max(1.0, self.current_speed)
        # Additional queue delay: each queued vehicle adds approx 1.5 seconds clearance time
        queue_delay = self.queue_length * 1.5
        return traversal_time + queue_delay

    @property
    def congestion_level(self) -> str:
        """Classifies congestion into LOW, MODERATE, HIGH, SEVERE."""
        d = self.density
        if d < CONGESTION_LEVELS["LOW"]:
            return "LOW"
        elif d < CONGESTION_LEVELS["MODERATE"]:
            return "MODERATE"
        elif d < CONGESTION_LEVELS["HIGH"]:
            return "HIGH"
        else:
            return "SEVERE"

    def can_accommodate(self) -> bool:
        """Check if segment has space for another vehicle."""
        return self.vehicle_count < self.capacity

    def add_vehicle(self, vehicle_id: str) -> bool:
        """Adds vehicle to segment if capacity permits, else returns False."""
        if vehicle_id in self.vehicles:
            return True
        if self.can_accommodate():
            self.vehicles.append(vehicle_id)
            return True
        return False

    def remove_vehicle(self, vehicle_id: str) -> bool:
        """Removes vehicle from this segment."""
        if vehicle_id in self.vehicles:
            self.vehicles.remove(vehicle_id)
            return True
        return False

    def add_to_queue(self, vehicle_id: str) -> None:
        """Adds vehicle to entrance queue if not already queued."""
        if vehicle_id not in self.queue:
            self.queue.append(vehicle_id)

    def remove_from_queue(self, vehicle_id: str) -> bool:
        """Removes vehicle from entrance queue."""
        if vehicle_id in self.queue:
            self.queue.remove(vehicle_id)
            return True
        return False

    def reset(self) -> None:
        """Reset dynamic states to clean initial condition."""
        self.vehicles.clear()
        self.queue.clear()
        self.toll = 0.0
        self.current_lanes = self.base_lanes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "road_id": self.road_id,
            "start_node": self.start_node,
            "end_node": self.end_node,
            "length": self.length,
            "free_flow_speed": self.free_flow_speed,
            "base_lanes": self.base_lanes,
            "current_lanes": self.current_lanes,
            "capacity": self.capacity,
            "vehicle_count": self.vehicle_count,
            "queue_length": self.queue_length,
            "density": round(self.density, 3),
            "current_speed": round(self.current_speed, 2),
            "free_flow_time": round(self.free_flow_time, 2),
            "estimated_travel_time": round(self.estimated_travel_time, 2),
            "congestion_level": self.congestion_level,
            "toll": round(self.toll, 2),
            "paired_road_id": self.paired_road_id
        }


class RoadNetwork:
    """
    Complete Smart City Urban Road Network managed through a NetworkX DiGraph.
    """
    def __init__(self, name: str = "SmartCityNet"):
        self.name = name
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, Intersection] = {}
        self.roads: Dict[str, RoadSegment] = {}
        self._edge_to_road: Dict[Tuple[str, str], str] = {}

    def add_intersection(self, node_id: str, name: str, x: float, y: float) -> Intersection:
        """Adds an intersection node to the network."""
        intersection = Intersection(node_id=node_id, name=name, x=x, y=y)
        self.nodes[node_id] = intersection
        self.graph.add_node(node_id, pos=(x, y), name=name, obj=intersection)
        return intersection

    def add_road_segment(
        self,
        road_id: str,
        start_node: str,
        end_node: str,
        length: float,
        free_flow_speed: float = 13.89,  # ~50 km/h
        base_lanes: int = 2,
        capacity_per_lane: int = 6,
        paired_road_id: Optional[str] = None
    ) -> RoadSegment:
        """Adds a directed road segment between two intersections."""
        if start_node not in self.nodes or end_node not in self.nodes:
            raise ValueError(f"Nodes {start_node} and {end_node} must exist in the network.")
        
        road = RoadSegment(
            road_id=road_id,
            start_node=start_node,
            end_node=end_node,
            length=length,
            free_flow_speed=free_flow_speed,
            base_lanes=base_lanes,
            current_lanes=base_lanes,
            capacity_per_lane=capacity_per_lane,
            paired_road_id=paired_road_id
        )
        self.roads[road_id] = road
        self._edge_to_road[(start_node, end_node)] = road_id
        
        self.nodes[start_node].connected_roads.append(road_id)
        self.nodes[end_node].connected_roads.append(road_id)
        
        self.graph.add_edge(
            start_node,
            end_node,
            road_id=road_id,
            length=length,
            weight=road.free_flow_time,
            obj=road
        )
        return road

    def add_bidirectional_road(
        self,
        id_ab: str,
        id_ba: str,
        node_a: str,
        node_b: str,
        length: float,
        free_flow_speed: float = 13.89,
        lanes_each: int = 2,
        capacity_per_lane: int = 6
    ) -> Tuple[RoadSegment, RoadSegment]:
        """Creates a bidirectional pair of roads with dynamic lane borrowing capability."""
        road_ab = self.add_road_segment(
            road_id=id_ab,
            start_node=node_a,
            end_node=node_b,
            length=length,
            free_flow_speed=free_flow_speed,
            base_lanes=lanes_each,
            capacity_per_lane=capacity_per_lane,
            paired_road_id=id_ba
        )
        road_ba = self.add_road_segment(
            road_id=id_ba,
            start_node=node_b,
            end_node=node_a,
            length=length,
            free_flow_speed=free_flow_speed,
            base_lanes=lanes_each,
            capacity_per_lane=capacity_per_lane,
            paired_road_id=id_ab
        )
        return road_ab, road_ba

    def get_road_between(self, start_node: str, end_node: str) -> Optional[RoadSegment]:
        """Retrieves RoadSegment object connecting start_node to end_node."""
        road_id = self._edge_to_road.get((start_node, end_node))
        return self.roads.get(road_id) if road_id else None

    def get_road(self, road_id: str) -> Optional[RoadSegment]:
        """Retrieves RoadSegment by its road_id."""
        return self.roads.get(road_id)

    def get_intersection(self, node_id: str) -> Optional[Intersection]:
        """Retrieves Intersection by node_id."""
        return self.nodes.get(node_id)

    def get_outgoing_roads(self, node_id: str) -> List[RoadSegment]:
        """Returns all road segments originating from node_id."""
        outgoing = []
        for neighbor in self.graph.successors(node_id):
            road = self.get_road_between(node_id, neighbor)
            if road:
                outgoing.append(road)
        return outgoing

    def update_graph_weights(
        self,
        cost_type: str = "travel_time",
        include_toll: bool = False,
        toll_weight: float = 1.0
    ) -> None:
        """
        Updates the NetworkX edge weights based on real-time road conditions.
        cost_type: 'distance', 'travel_time', or 'congestion_aware'
        """
        for u, v, data in self.graph.edges(data=True):
            road: RoadSegment = data["obj"]
            if cost_type == "distance":
                weight = road.length
            elif cost_type == "travel_time":
                weight = road.estimated_travel_time
            elif cost_type == "congestion_aware":
                # Quadratic congestion penalty
                congestion_multiplier = 1.0 + 2.5 * (road.density ** 2)
                weight = road.estimated_travel_time * congestion_multiplier
            else:
                weight = road.estimated_travel_time
            
            if include_toll and road.toll > 0:
                weight += (road.toll * toll_weight)
                
            data["weight"] = max(0.1, weight)

    def reset_network(self) -> None:
        """Resets all road segment dynamic loads, queues, tolls and lanes."""
        for road in self.roads.values():
            road.reset()
        self.update_graph_weights("travel_time")

    def get_network_summary(self) -> Dict[str, Any]:
        """Summary statistics of the road network."""
        total_roads = len(self.roads)
        total_vehicles = sum(r.vehicle_count for r in self.roads.values())
        total_capacity = sum(r.capacity for r in self.roads.values())
        total_queue = sum(r.queue_length for r in self.roads.values())
        avg_density = (total_vehicles / max(1, total_capacity)) if total_capacity > 0 else 0.0
        
        congestion_counts = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "SEVERE": 0}
        for r in self.roads.values():
            congestion_counts[r.congestion_level] += 1
            
        return {
            "name": self.name,
            "num_intersections": len(self.nodes),
            "num_roads": total_roads,
            "total_vehicles": total_vehicles,
            "total_capacity": total_capacity,
            "total_queued": total_queue,
            "average_density": round(avg_density, 3),
            "congestion_breakdown": congestion_counts
        }
