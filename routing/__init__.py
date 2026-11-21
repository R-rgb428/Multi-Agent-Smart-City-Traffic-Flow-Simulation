"""
Routing module for Multi-Agent Smart City Traffic Simulation.
Provides Dijkstra, A*, and heuristic multi-criteria route planning.
"""
from routing.route_planner import RoutePlanner, RouteResult

__all__ = ["RoutePlanner", "RouteResult"]
