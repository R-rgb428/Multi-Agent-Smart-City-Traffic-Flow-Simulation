"""
Unit tests for Performance Evaluation and Comparison module.
"""
import pytest
from simulation.engine import SimulationEngine
from evaluation.metrics import calculate_simulation_metrics
from evaluation.comparison import StrategyComparator
from config import SCENARIO_LOW


def test_performance_metrics_calculation():
    engine = SimulationEngine(max_ticks=30)
    engine.setup(scenario_name=SCENARIO_LOW, vehicle_count=6, strategy_name="Independent", seed=42)
    engine.run_to_completion(max_ticks=30)

    metrics = calculate_simulation_metrics(engine)
    assert metrics.total_vehicles == 6
    assert metrics.simulation_ticks > 0
    assert metrics.average_travel_time >= 0.0
    assert metrics.total_travel_time >= 0.0
    assert 0.0 <= metrics.average_density <= 1.0
    assert metrics.average_queue_length >= 0.0
    assert metrics.throughput >= 0
    assert metrics.average_delay >= 0.0

    m_dict = metrics.to_dict()
    assert "Completed Avg Travel Time (s)" in m_dict
    assert "All-Departed Avg Time (s)" in m_dict
    assert "Throughput (Completed)" in m_dict


def test_strategy_comparator_run():
    comparator = StrategyComparator()
    # Run a quick 20-tick comparison on Low traffic scenario
    benchmark = comparator.run_comparison(
        scenario_name=SCENARIO_LOW,
        vehicle_count=6,
        max_ticks=20,
        seed=42
    )

    assert len(benchmark.metrics_by_strategy) == 5
    assert "Independent" in benchmark.metrics_by_strategy
    assert "Combined" in benchmark.metrics_by_strategy
    assert not benchmark.comparison_table.empty
    assert len(benchmark.comparison_table) == 5
