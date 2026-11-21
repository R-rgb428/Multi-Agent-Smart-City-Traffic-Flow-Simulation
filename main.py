"""
CLI Entrypoint and Execution Runner for Multi-Agent Smart City Traffic Flow Simulation.
Group 17 — Artificial Intelligence Foundations.
"""
import sys
import argparse
import subprocess
import pandas as pd

from simulation.engine import SimulationEngine
from evaluation.comparison import StrategyComparator
from config import SCENARIO_NORMAL, SCENARIO_RUSH_HOUR


def run_cli_demo(scenario: str = SCENARIO_NORMAL, vehicles: int = 35, ticks: int = 120):
    """Executes a console-based multi-agent simulation demonstration."""
    print("=" * 70)
    print(" MULTI-AGENT SMART CITY TRAFFIC FLOW SIMULATION ")
    print(" Group 17 — Artificial Intelligence Foundations ")
    print("=" * 70)
    print(f"Scenario: {scenario} | Fleet Size: {vehicles} Vehicles | Max Ticks: {ticks}\n")

    comparator = StrategyComparator(network_type="smart_city")
    print("Executing benchmark across all 5 strategies under identical seed (42)...")
    bench = comparator.run_comparison(
        scenario_name=scenario,
        vehicle_count=vehicles,
        max_ticks=ticks,
        seed=42
    )

    print("\n--- COMPARATIVE PERFORMANCE EVALUATION (6 Core Metrics) ---")
    print(bench.comparison_table.to_string(index=False))

    print("\n--- PERCENTAGE IMPROVEMENT RELATIVE TO INDEPENDENT ROUTING ---")
    print(bench.improvement_table.to_string(index=False))

    print("\n" + "=" * 70)
    print("To launch the interactive web dashboard, run:")
    print("  streamlit run app.py")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Smart City Traffic Simulation")
    parser.add_argument("--benchmark", action="store_true", help="Run comparative benchmark in terminal")
    parser.add_argument("--scenario", type=str, default=SCENARIO_NORMAL, help="Scenario name")
    parser.add_argument("--vehicles", type=int, default=35, help="Number of vehicles")
    parser.add_argument("--ticks", type=int, default=120, help="Simulation ticks")
    parser.add_argument("--test", action="store_true", help="Run pytest test suite")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit dashboard")

    args = parser.parse_args()

    if args.test:
        subprocess.run(["python", "-m", "pytest", "tests/"])
    elif args.ui:
        subprocess.run(["streamlit", "run", "app.py"])
    else:
        run_cli_demo(scenario=args.scenario, vehicles=args.vehicles, ticks=args.ticks)


if __name__ == "__main__":
    main()
