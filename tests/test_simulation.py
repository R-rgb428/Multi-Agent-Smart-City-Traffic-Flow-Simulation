"""
Unit tests for Simulation Engine module.
"""
import pytest
from simulation.engine import SimulationEngine, SimulationState
from config import SCENARIO_LOW


def test_simulation_lifecycle():
    engine = SimulationEngine()
    engine.setup(scenario_name=SCENARIO_LOW, vehicle_count=10, strategy_name="Independent", seed=42)
    assert engine.state == SimulationState.READY
    assert engine.tick == 0
    assert len(engine.fleet_manager.vehicles) == 10

    # Step forward
    res = engine.step()
    assert res["tick"] == 1
    assert "active_vehicles" in res

    # Pause and resume
    engine.start()
    assert engine.state == SimulationState.RUNNING
    engine.pause()
    assert engine.state == SimulationState.PAUSED
    engine.resume()
    assert engine.state == SimulationState.RUNNING


def test_simulation_run_to_completion():
    engine = SimulationEngine(max_ticks=50)
    engine.setup(scenario_name=SCENARIO_LOW, vehicle_count=8, strategy_name="Combined", seed=42)
    summary = engine.run_to_completion(max_ticks=50)

    assert summary["strategy"] == "Combined"
    assert summary["ticks_elapsed"] > 0
    assert summary["total_vehicles"] == 8
    assert engine.state in (SimulationState.COMPLETED, SimulationState.RUNNING)
