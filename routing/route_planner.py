"""
Route planning algorithms: Dijkstra, A*, and multi-criteria cost functions.
"""
from __future__ import annotations
import math
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import networkx as nx

from road_network.network import RoadNetwork, RoadSegment


@dataclass
class RouteResult:
    """Encapsulates the outcome of a routing query."""
    path: List[str]                  # List of intersection node IDs [origin, ..., destination]
    road_ids: List[str]              # List of road IDs traversed
    total_distance: float            # meters
    estimated_travel_time: float     # seconds
    total_toll: float                # virtual currency
    algorithm: str                   # "dijkstra" or "astar"
    cost_criterion: str              # "distance", "travel_time", "congestion_aware"
    found: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "road_ids": self.road_ids,
            "total_distance": round(self.total_distance, 1),
            "estimated_travel_time": round(self.estimated_travel_time, 1),
            "total_toll": round(self.total_toll, 2),
            "algorithm": self.algorithm,
            "cost_criterion": self.cost_criterion,
            "found": self.found,
            "error_message": self.error_message
        }


class RoutePlanner:
    """
    Intelligent route planner supporting Dijkstra, A*, and various objective functions.
    """
    def __init__(self, network: RoadNetwork):
        self.network = network

    def _heuristic(self, node_a: str, node_b: str, max_speed: float = 22.22) -> float:
        """
        Admissible Euclidean distance heuristic for A* algorithm.
        Estimates the minimum time to reach node_b from node_a.
        """
        inter_a = self.network.get_intersection(node_a)
        inter_b = self.network.get_intersection(node_b)
        if not inter_a or not inter_b:
            return 0.0
        
        dx = inter_a.x - inter_b.x
        dy = inter_a.y - inter_b.y
        dist = math.hypot(dx, dy)
        return dist / max(1.0, max_speed)

    def calculate_edge_cost(
        self,
        road: RoadSegment,
        criterion: str = "travel_time",
        include_toll: bool = False,
        toll_sensitivity: float = 1.0
    ) -> float:
        """
        Calculates edge cost based on the chosen strategy.
        """
        if criterion == "distance":
            cost = road.length
        elif criterion == "free_flow":
            cost = road.free_flow_time
        elif criterion == "travel_time":
            cost = road.estimated_travel_time
        elif criterion == "congestion_aware":
            # Penalizes high density non-linearly
            penalty = 1.0 + 3.0 * (road.density ** 2)
            cost = road.estimated_travel_time * penalty
        else:
            cost = road.estimated_travel_time

        if include_toll and road.toll > 0:
            cost += (road.toll * toll_sensitivity)

        return max(0.1, cost)

    def plan_route_dijkstra(
        self,
        origin: str,
        destination: str,
        criterion: str = "travel_time",
        include_toll: bool = False,
        toll_sensitivity: float = 1.0
    ) -> RouteResult:
        """
        Computes optimal route using Dijkstra's algorithm.
        """
        if origin not in self.network.nodes or destination not in self.network.nodes:
            return RouteResult([], [], 0.0, 0.0, 0.0, "dijkstra", criterion, False, "Invalid origin or destination.")

        if origin == destination:
            return RouteResult([origin], [], 0.0, 0.0, 0.0, "dijkstra", criterion, True)

        # Priority queue stores (cumulative_cost, current_node, path)
        pq: List[Tuple[float, str, List[str]]] = [(0.0, origin, [origin])]
        best_costs: Dict[str, float] = {origin: 0.0}

        while pq:
            cost, current_node, path = heapq.heappop(pq)

            if current_node == destination:
                return self._assemble_result(path, "dijkstra", criterion)

            if cost > best_costs.get(current_node, float('inf')):
                continue

            for road in self.network.get_outgoing_roads(current_node):
                neighbor = road.end_node
                edge_cost = self.calculate_edge_cost(road, criterion, include_toll, toll_sensitivity)
                new_cost = cost + edge_cost

                if new_cost < best_costs.get(neighbor, float('inf')):
                    best_costs[neighbor] = new_cost
                    heapq.heappush(pq, (new_cost, neighbor, path + [neighbor]))

        return RouteResult([], [], 0.0, 0.0, 0.0, "dijkstra", criterion, False, "No route found between nodes.")

    def plan_route_astar(
        self,
        origin: str,
        destination: str,
        criterion: str = "travel_time",
        include_toll: bool = False,
        toll_sensitivity: float = 1.0
    ) -> RouteResult:
        """
        Computes optimal route using A* search with Euclidean distance heuristic.
        """
        if origin not in self.network.nodes or destination not in self.network.nodes:
            return RouteResult([], [], 0.0, 0.0, 0.0, "astar", criterion, False, "Invalid origin or destination.")

        if origin == destination:
            return RouteResult([origin], [], 0.0, 0.0, 0.0, "astar", criterion, True)

        # Priority queue stores (f_score, g_score, current_node, path)
        h_start = self._heuristic(origin, destination)
        pq: List[Tuple[float, float, str, List[str]]] = [(h_start, 0.0, origin, [origin])]
        g_scores: Dict[str, float] = {origin: 0.0}

        while pq:
            f, g, current_node, path = heapq.heappop(pq)

            if current_node == destination:
                return self._assemble_result(path, "astar", criterion)

            if g > g_scores.get(current_node, float('inf')):
                continue

            for road in self.network.get_outgoing_roads(current_node):
                neighbor = road.end_node
                edge_cost = self.calculate_edge_cost(road, criterion, include_toll, toll_sensitivity)
                tentative_g = g + edge_cost

                if tentative_g < g_scores.get(neighbor, float('inf')):
                    g_scores[neighbor] = tentative_g
                    h = self._heuristic(neighbor, destination)
                    f_score = tentative_g + h
                    heapq.heappush(pq, (f_score, tentative_g, neighbor, path + [neighbor]))

        return RouteResult([], [], 0.0, 0.0, 0.0, "astar", criterion, False, "No route found between nodes.")

    def plan_route(
        self,
        origin: str,
        destination: str,
        algorithm: str = "astar",
        criterion: str = "travel_time",
        include_toll: bool = False,
        toll_sensitivity: float = 1.0
    ) -> RouteResult:
        """Unified entry point for route planning."""
        if algorithm == "dijkstra":
            return self.plan_route_dijkstra(origin, destination, criterion, include_toll, toll_sensitivity)
        else:
            return self.plan_route_astar(origin, destination, criterion, include_toll, toll_sensitivity)

    def find_alternative_routes(
        self,
        origin: str,
        destination: str,
        max_alternatives: int = 3
    ) -> List[RouteResult]:
        """
        Finds up to k alternative paths using NetworkX shortest simple paths.
        """
        results: List[RouteResult] = []
        if origin not in self.network.nodes or destination not in self.network.nodes or origin == destination:
            return results

        try:
            # Generate paths ordered by free-flow travel time
            paths = list(nx.shortest_simple_paths(
                self.network.graph, origin, destination, weight="weight"
            ))
            for p in paths[:max_alternatives]:
                res = self._assemble_result(p, "alternative", "travel_time")
                if res.found:
                    results.append(res)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        return results

    def compare_routing_strategies(
        self,
        origin: str,
        destination: str
    ) -> Dict[str, RouteResult]:
        """
        Compares route choices under different criteria:
        1. Shortest Distance (Independent naive)
        2. Free-Flow Time (Independent baseline)
        3. Dynamic Travel Time (Congestion-aware uncoordinated)
        4. Coordinated (Congestion-aware + Tolls)
        """
        return {
            "Shortest Distance": self.plan_route(origin, destination, "astar", "distance"),
            "Free-Flow Time": self.plan_route(origin, destination, "astar", "free_flow"),
            "Current Travel Time": self.plan_route(origin, destination, "astar", "travel_time"),
            "Coordinated (Toll & Congestion)": self.plan_route(origin, destination, "astar", "congestion_aware", include_toll=True)
        }

    def _assemble_result(self, path: List[str], algorithm: str, criterion: str) -> RouteResult:
        """Assembles metrics along the selected node sequence."""
        total_dist = 0.0
        total_time = 0.0
        total_toll = 0.0
        road_ids: List[str] = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            road = self.network.get_road_between(u, v)
            if road:
                road_ids.append(road.road_id)
                total_dist += road.length
                total_time += road.estimated_travel_time
                total_toll += road.toll

        return RouteResult(
            path=path,
            road_ids=road_ids,
            total_distance=total_dist,
            estimated_travel_time=total_time,
            total_toll=total_toll,
            algorithm=algorithm,
            cost_criterion=criterion,
            found=True
        )
