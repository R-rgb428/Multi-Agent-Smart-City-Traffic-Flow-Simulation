"""
Unit tests for Visualization components (city map and charts).
"""
import pytest
from road_network.scenarios import build_smart_city_network
from routing.route_planner import RoutePlanner
from agents.vehicle_manager import VehicleManager
from simulation.engine import SimulationEngine
from visualization.city_map import render_city_network_map
from visualization.charts import (
    render_metrics_timeline,
    render_speed_density_trend,
    render_strategy_comparison_chart,
    render_radar_comparison
)
from evaluation.comparison import StrategyComparator


def test_city_map_rendering():
    net = build_smart_city_network()
    planner = RoutePlanner(net)
    manager = VehicleManager(net, planner)
    manager.generate_scenario_fleet("Low Traffic", 5, seed=42)

    fig = render_city_network_map(net, manager)
    assert fig is not None
    assert len(fig.data) > 0


def test_charts_rendering():
    engine = SimulationEngine(max_ticks=10)
    engine.setup("Low Traffic", 4, "Independent", seed=42)
    engine.run_to_completion(max_ticks=10)

    df_hist = engine.monitor.history_to_dataframe()
    fig1 = render_metrics_timeline(df_hist)
    assert fig1 is not None

    fig2 = render_speed_density_trend(df_hist)
    assert fig2 is not None

    comparator = StrategyComparator()
    bench = comparator.run_comparison("Low Traffic", 4, max_ticks=10, seed=42)
    fig3 = render_strategy_comparison_chart(bench.comparison_table)
    assert fig3 is not None

    fig4 = render_radar_comparison(bench.metrics_by_strategy)
    assert fig4 is not None
