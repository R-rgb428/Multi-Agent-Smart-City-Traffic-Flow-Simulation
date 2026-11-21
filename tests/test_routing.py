"""
Unit tests for Route Selection module.
"""
import pytest
from road_network.scenarios import build_smart_city_network
from routing.route_planner import RoutePlanner


@pytest.fixture
def planner():
    net = build_smart_city_network()
    return RoutePlanner(net)


def test_dijkstra_valid_path(planner):
    res = planner.plan_route_dijkstra("NW_RES", "SE_SUB", criterion="distance")
    assert res.found is True
    assert res.path[0] == "NW_RES"
    assert res.path[-1] == "SE_SUB"
    assert res.total_distance > 0.0
    assert len(res.road_ids) == len(res.path) - 1


def test_astar_valid_path(planner):
    res = planner.plan_route_astar("NW_RES", "SE_SUB", criterion="travel_time")
    assert res.found is True
    assert res.path[0] == "NW_RES"
    assert res.path[-1] == "SE_SUB"
    assert res.estimated_travel_time > 0.0


def test_routing_invalid_nodes(planner):
    res = planner.plan_route("INVALID_1", "INVALID_2")
    assert res.found is False


def test_alternative_routes(planner):
    alternatives = planner.find_alternative_routes("NW_RES", "SE_SUB", max_alternatives=3)
    assert len(alternatives) >= 2
    for alt in alternatives:
        assert alt.found is True
        assert alt.path[0] == "NW_RES"
        assert alt.path[-1] == "SE_SUB"


def test_compare_routing_strategies(planner):
    comparison = planner.compare_routing_strategies("NW_RES", "SE_SUB")
    assert "Shortest Distance" in comparison
    assert "Free-Flow Time" in comparison
    assert "Current Travel Time" in comparison
    assert "Coordinated (Toll & Congestion)" in comparison
    for k, v in comparison.items():
        assert v.found is True
