"""
Integration tests verifying end-to-end simulation behavior, intersection queueing,
en-route rerouting, coordination mechanisms, and multi-scenario reproducibility.
"""
import pytest
from road_network.scenarios import build_smart_city_network
from agents.vehicle import VehicleAgent
from simulation.engine import SimulationEngine, SimulationState
from evaluation.comparison import StrategyComparator
from config import SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN


def test_vehicle_does_not_get_stuck_at_intermediate_intersection():
    """Regression test: vehicle queued at an intermediate intersection must advance when space opens."""
    net = build_smart_city_network()
    # Route: NW_RES -> N_GATE -> RIVER_BR
    road1 = net.get_road_between("NW_RES", "N_GATE")
    road2 = net.get_road_between("N_GATE", "RIVER_BR")
    assert road1 is not None and road2 is not None

    # Fill road2 to full capacity so vehicle must queue at N_GATE
    for i in range(road2.capacity):
        road2.add_vehicle(f"BLOCKER_{i}")

    veh = VehicleAgent(
        vehicle_id="V_INTERMEDIATE_WAIT",
        origin="NW_RES",
        destination="RIVER_BR",
        selected_route=["NW_RES", "N_GATE", "RIVER_BR"]
    )

    # Step until vehicle traverses road1 and queues at N_GATE for road2
    for tick in range(1, 50):
        veh.step(net, delta_t=3.0, current_tick=tick)
        if veh.completion_status == "WAITING":
            break

    assert veh.completion_status == "WAITING"
    assert veh.current_node == "N_GATE"
    assert veh.route_index == 1
    assert "V_INTERMEDIATE_WAIT" in road2.queue

    # Free 1 spot on road2
    road2.remove_vehicle("BLOCKER_0")
    assert road2.can_accommodate() is True

    # Next step should enter road2 and eventually complete at RIVER_BR
    veh.step(net, delta_t=3.0, current_tick=51)
    assert veh.completion_status == "EN_ROUTE"
    assert veh.current_road_id == road2.road_id

    for tick in range(52, 200):
        veh.step(net, delta_t=3.0, current_tick=tick)
        if veh.completion_status == "COMPLETED":
            break

    assert veh.completion_status == "COMPLETED"
    assert veh.current_node == "RIVER_BR"


def test_reroute_while_en_route_maintains_connectivity():
    """En-route vehicle rerouting must plan from target_node and complete without teleporting."""
    net = build_smart_city_network()
    veh = VehicleAgent(
        vehicle_id="V_REROUTE",
        origin="NW_RES",
        destination="S_CIVIC",
        selected_route=["NW_RES", "N_GATE", "RIVER_BR", "DOWNTOWN", "S_CIVIC"]
    )

    # Enter first road NW_RES -> N_GATE
    veh.step(net, delta_t=3.0, current_tick=1)
    assert veh.completion_status == "EN_ROUTE"
    assert veh.target_node == "N_GATE"

    # Reroute from target_node (N_GATE) via NE_TECH -> E_FIN -> SE_SUB -> S_CIVIC
    new_leg = ["N_GATE", "NE_TECH", "E_FIN", "SE_SUB", "S_CIVIC"]
    assert veh.update_route(new_leg, reason="Test detour", network=net) is True
    assert veh.reroute_count == 1

    for tick in range(2, 180):
        veh.step(net, delta_t=3.0, current_tick=tick)
        if veh.completion_status == "COMPLETED":
            break

    assert veh.completion_status == "COMPLETED"
    assert veh.current_node == "S_CIVIC"


def test_congestion_pricing_alters_behavior_independently():
    """Congestion pricing alone (advisories off) must levy tolls and trigger reroutes in Rush Hour."""
    eng_ind = SimulationEngine(max_ticks=120)
    eng_ind.setup(SCENARIO_RUSH_HOUR, vehicle_count=60, strategy_name="Independent", seed=42)
    res_ind = eng_ind.run_to_completion(120)

    eng_price = SimulationEngine(max_ticks=120)
    eng_price.setup(SCENARIO_RUSH_HOUR, vehicle_count=60, strategy_name="Congestion Pricing", seed=42)
    res_price = eng_price.run_to_completion(120)

    assert len(eng_price.coordinator.pricing_system.events) > 0
    total_reroutes = sum(v.reroute_count for v in eng_price.fleet_manager.vehicles.values())
    assert total_reroutes > 0
    assert res_price["completed_vehicles"] != res_ind["completed_vehicles"] or res_price["average_travel_time"] != res_ind["average_travel_time"]


def test_dynamic_lane_conservation_invariant():
    """Dynamic lane assignment must always preserve total bidirectional lanes."""
    eng = SimulationEngine(max_ticks=100)
    eng.setup(SCENARIO_RUSH_HOUR, vehicle_count=60, strategy_name="Dynamic Lanes", seed=42)

    for _ in range(100):
        eng.step()
        for road in eng.network.roads.values():
            if road.paired_road_id:
                paired = eng.network.get_road(road.paired_road_id)
                assert road.current_lanes >= 1
                assert paired.current_lanes >= 1
                assert (road.current_lanes + paired.current_lanes) == (road.base_lanes + paired.base_lanes)


def test_combined_coordination_activates_all_three_mechanisms():
    """Combined strategy must activate dynamic lanes, congestion pricing, and route advisories."""
    eng = SimulationEngine(max_ticks=120)
    eng.setup(SCENARIO_RUSH_HOUR, vehicle_count=85, strategy_name="Combined", seed=42)
    eng.run_to_completion(120)

    assert len(eng.coordinator.lane_system.events) > 0
    assert len(eng.coordinator.pricing_system.events) > 0
    assert len(eng.coordinator.advisory_system.events) > 0


def test_reproducibility_across_all_scenarios():
    """Identical seeds must produce bit-for-bit identical metrics across all 4 scenarios."""
    comp = StrategyComparator()
    for scen in [SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN]:
        run1 = comp.run_comparison(scen, vehicle_count=25, max_ticks=60, seed=123)
        run2 = comp.run_comparison(scen, vehicle_count=25, max_ticks=60, seed=123)
        assert run1.comparison_table.equals(run2.comparison_table)


def test_staggered_arrivals_and_rush_hour_burst():
    """Vehicles must respect scheduled_departure_tick and not accrue travel_time before departing."""
    eng = SimulationEngine(max_ticks=50)
    eng.setup(SCENARIO_RUSH_HOUR, vehicle_count=30, strategy_name="Independent", seed=42, arrival_interval=2)

    scheduled_ticks = [v.scheduled_departure_tick for v in eng.fleet_manager.vehicles.values()]
    assert max(scheduled_ticks) > 0, "Rush hour fleet should have staggered departure ticks"

    # Step 2 ticks and verify vehicles scheduled after tick 2 remain PENDING with 0 travel_time
    eng.step()
    eng.step()
    for v in eng.fleet_manager.vehicles.values():
        if v.scheduled_departure_tick > 2:
            assert v.completion_status == "PENDING"
            assert v.travel_time == 0.0


def test_unfinished_metrics_and_multi_seed_comparison():
    """Evaluation must report completed vs unfinished vehicles and aggregate multi-seed mean +/- std."""
    comp = StrategyComparator()
    multi = comp.run_multi_seed_comparison(
        scenario_name=SCENARIO_NORMAL,
        vehicle_count=20,
        max_ticks=30,
        seeds=[42, 101]
    )
    assert len(multi.runs_by_seed) == 2
    assert len(multi.summary_table) == 5
    assert "All-Departed Avg (s)" in multi.summary_table.columns
    assert "Total Journey Time (s)" in multi.summary_table.columns

    # Check single-run metrics distinguish simulation_duration_sec vs total_travel_time
    m = multi.runs_by_seed[0].metrics_by_strategy["Independent"]
    assert m.throughput + m.unfinished_vehicles == m.total_vehicles
    assert m.simulation_duration_sec > 0
