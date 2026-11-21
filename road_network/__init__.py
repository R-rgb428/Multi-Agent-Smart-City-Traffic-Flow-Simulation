"""
Road Network Module for Smart City Traffic Simulation.
Defines intersections, road segments, and network topologies using NetworkX.
"""
from road_network.network import Intersection, RoadSegment, RoadNetwork
from road_network.scenarios import build_smart_city_network, build_arterial_corridor_network

__all__ = [
    "Intersection",
    "RoadSegment",
    "RoadNetwork",
    "build_smart_city_network",
    "build_arterial_corridor_network"
]
