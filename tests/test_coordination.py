"""
Unit tests for AI Coordination module (Route Advisory, Pricing, Dynamic Lanes, Master Coordinator).
"""
import pytest
from road_network.scenarios import build_smart_city_network, build_arterial_corridor_network
from routing.route_planner import RoutePlanner
from agents.vehicle import VehicleAgent
from agents.vehicle_manager import VehicleManager
from monitoring.traffic_monitor import TrafficMonitor
from coordination.route_advisory import RouteAdvisorySystem
from coordination.congestion_pricing import CongestionPricingSystem
from coordination.dynamic_lane import DynamicLaneAssignmentSystem
from coordination.coordinator import AICoordinator


def test_route_advisory():
    net = build_smart_city_network()
    planner = RoutePlanner(net)
    advisory_sys = RouteAdvisorySystem(density_threshold=0.6, switch_cost_penalty=5.0)

    # Artificially congest the central river bridge
    road = net.get_road_between("N_GATE", "RIVER_BR")
    assert road is not None
    for i in range(road.capacity):
        road.add_vehicle(f"BLOCKER_{i}")

    # Vehicle planning to go through the bridge
    veh = VehicleAgent(
        vehicle_id="V_ADVISE",
        origin="NW_RES",
        destination="SE_SUB",
        selected_route=["NW_RES", "N_GATE", "RIVER_BR", "DOWNTOWN", "S_CIVIC", "SE_SUB"]
    )
    veh.current_node = "NW_RES"
    veh.completion_status = "EN_ROUTE"

    events = advisory_sys.evaluate_and_advise(
        tick=1, network=net, vehicles=[veh], planner=planner
    )
    assert len(events) >= 1
    # Check that an alternative bypass route was evaluated
    assert len(advisory_sys.events) >= 1


def test_congestion_pricing():
    net = build_smart_city_network()
    pricing_sys = CongestionPricingSystem(density_threshold=0.6, base_multiplier=20.0)

    road = list(net.roads.values())[0]
    # No congestion -> toll = 0
    pricing_sys.update_tolls(tick=0, network=net)
    assert road.toll == 0.0

    # Fill to 90%
    for i in range(int(road.capacity * 0.9)):
        road.add_vehicle(f"V_{i}")

    events = pricing_sys.update_tolls(tick=1, network=net)
    assert road.toll > 0.0
    assert len(events) >= 1


def test_dynamic_lane_assignment():
    net = build_arterial_corridor_network()
    lane_sys = DynamicLaneAssignmentSystem(ratio_threshold=1.5, rebalance_interval=1)

    fwd_road = net.get_road_between("WEST_SUB", "W_PLAZA")
    rev_road = net.get_road_between("W_PLAZA", "WEST_SUB")
    assert fwd_road is not None and rev_road is not None
    total_lanes = fwd_road.base_lanes + rev_road.base_lanes

    # Heavily load forward direction
    for i in range(fwd_road.capacity):
        fwd_road.add_vehicle(f"FWD_{i}")

    events = lane_sys.evaluate_and_reallocate(tick=1, network=net)
    assert len(events) >= 1
    # Forward should gain a lane, reverse should lose one
    assert fwd_road.current_lanes > fwd_road.base_lanes
    assert rev_road.current_lanes < rev_road.base_lanes
    assert fwd_road.current_lanes + rev_road.current_lanes == total_lanes


def test_ai_coordinator_presets():
    net = build_smart_city_network()
    planner = RoutePlanner(net)
    manager = VehicleManager(net, planner)
    monitor = TrafficMonitor(net)
    coordinator = AICoordinator()

    coordinator.set_strategy("Combined")
    assert coordinator.config.enable_advisories is True
    assert coordinator.config.enable_pricing is True
    assert coordinator.config.enable_dynamic_lanes is True

    # Run cycle
    res = coordinator.step(tick=1, network=net, fleet_manager=manager, monitor=monitor, planner=planner)
    assert "lane_events" in res
    assert "pricing_events" in res
    assert "advisory_events" in res
