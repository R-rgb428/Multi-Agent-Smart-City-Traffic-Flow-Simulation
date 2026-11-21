"""
Unit tests for Traffic Monitor module.
"""
import pytest
from road_network.scenarios import build_smart_city_network
from routing.route_planner import RoutePlanner
from agents.vehicle_manager import VehicleManager
from monitoring.traffic_monitor import TrafficMonitor


def test_traffic_monitor_updates():
    net = build_smart_city_network()
    planner = RoutePlanner(net)
    manager = VehicleManager(net, planner)
    monitor = TrafficMonitor(net)

    # Initial state
    snap = monitor.update(tick=0, fleet_manager=manager)
    assert snap.tick == 0
    assert snap.total_vehicles == 0
    assert snap.active_vehicles == 0
    assert len(monitor.get_all_road_snapshots()) == len(net.roads)

    # Add vehicles to a specific road
    road = list(net.roads.values())[0]
    for i in range(road.capacity):
        road.add_vehicle(f"V_{i}")

    snap_congested = monitor.update(tick=1, fleet_manager=manager)
    assert snap_congested.severe_roads_count >= 1
    assert road.road_id in snap_congested.bottlenecks

    congested_list = monitor.get_congested_roads(min_level="HIGH")
    assert any(s.road_id == road.road_id for s in congested_list)

    df = monitor.roads_to_dataframe()
    assert len(df) == len(net.roads)
