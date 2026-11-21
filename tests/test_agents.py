"""
Unit tests for Vehicle Agent System module.
"""
import pytest
from road_network.scenarios import build_smart_city_network
from routing.route_planner import RoutePlanner
from agents.vehicle import VehicleAgent
from agents.vehicle_manager import VehicleManager
from config import SCENARIO_LOW, SCENARIO_RUSH_HOUR


@pytest.fixture
def env():
    net = build_smart_city_network()
    planner = RoutePlanner(net)
    manager = VehicleManager(net, planner)
    return net, planner, manager


def test_vehicle_creation_and_movement(env):
    net, planner, manager = env
    route_res = planner.plan_route("NW_RES", "N_GATE")
    assert route_res.found is True

    veh = VehicleAgent(
        vehicle_id="V_TEST_1",
        origin="NW_RES",
        destination="N_GATE",
        selected_route=route_res.path,
        driving_behaviour="NORMAL"
    )
    veh.calculate_free_flow_time(net)
    assert veh.completion_status == "PENDING"

    # Step 1: should enter first road
    veh.step(net, delta_t=1.0, current_tick=1)
    assert veh.completion_status == "EN_ROUTE"
    assert veh.current_road_id is not None
    road = net.get_road(veh.current_road_id)
    assert "V_TEST_1" in road.vehicles

    # Step forward until destination reached
    ticks = 0
    while veh.completion_status != "COMPLETED" and ticks < 200:
        veh.step(net, delta_t=5.0, current_tick=ticks)
        ticks += 1

    assert veh.completion_status == "COMPLETED"
    assert veh.current_node == "N_GATE"
    assert "V_TEST_1" not in road.vehicles


def test_capacity_blocking_and_queue(env):
    net, planner, manager = env
    road = net.get_road_between("NW_RES", "N_GATE")
    assert road is not None
    # artifically fill the road
    for i in range(road.capacity):
        road.add_vehicle(f"FILLER_{i}")
    assert road.can_accommodate() is False

    # New vehicle trying to enter
    veh = VehicleAgent(
        vehicle_id="V_BLOCKED",
        origin="NW_RES",
        destination="N_GATE",
        selected_route=["NW_RES", "N_GATE"]
    )
    veh.step(net, delta_t=1.0, current_tick=1)
    assert veh.completion_status == "WAITING"
    assert "V_BLOCKED" in road.queue
    assert veh.waiting_time > 0


def test_vehicle_manager_fleet_generation(env):
    net, planner, manager = env
    fleet = manager.generate_scenario_fleet(
        scenario_name=SCENARIO_LOW,
        vehicle_count=10,
        seed=42
    )
    assert len(fleet) == 10
    assert len(manager.vehicles) == 10
    summary = manager.get_fleet_summary()
    assert summary["total_vehicles"] == 10
