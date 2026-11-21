"""
Unit tests for Road Network module.
"""
import pytest
from road_network.network import RoadNetwork, RoadSegment, Intersection
from road_network.scenarios import build_smart_city_network, build_arterial_corridor_network


def test_intersection_creation():
    net = RoadNetwork("TestNet")
    node = net.add_intersection("N1", "Node 1", 100.0, 200.0)
    assert node.node_id == "N1"
    assert node.x == 100.0
    assert node.y == 200.0
    assert "N1" in net.nodes
    assert "N1" in net.graph.nodes


def test_road_segment_properties():
    road = RoadSegment(
        road_id="R1",
        start_node="A",
        end_node="B",
        length=1000.0,
        free_flow_speed=20.0,
        base_lanes=2,
        capacity_per_lane=5
    )
    assert road.capacity == 10
    assert road.vehicle_count == 0
    assert road.density == 0.0
    assert road.congestion_level == "LOW"
    assert road.free_flow_time == 50.0

    # Add vehicles
    for i in range(5):
        assert road.add_vehicle(f"V{i}") is True
    assert road.vehicle_count == 5
    assert road.density == 0.5
    assert road.congestion_level == "MODERATE"

    # Fill to capacity
    for i in range(5, 10):
        assert road.add_vehicle(f"V{i}") is True
    assert road.vehicle_count == 10
    assert road.density == 1.0
    assert road.congestion_level == "SEVERE"
    assert road.can_accommodate() is False

    # Attempt to exceed capacity
    assert road.add_vehicle("V_OVERFLOW") is False


def test_smart_city_network_connectivity():
    net = build_smart_city_network()
    summary = net.get_network_summary()
    assert summary["num_intersections"] >= 10
    assert summary["num_roads"] >= 20

    # Verify every node has outgoing roads
    for node_id in net.nodes:
        outgoing = net.get_outgoing_roads(node_id)
        assert len(outgoing) > 0, f"Node {node_id} has no outgoing roads!"


def test_arterial_corridor_network():
    net = build_arterial_corridor_network()
    assert "WEST_SUB" in net.nodes
    assert "EAST_CBD" in net.nodes
    road = net.get_road_between("WEST_SUB", "W_PLAZA")
    assert road is not None
    assert road.paired_road_id is not None
