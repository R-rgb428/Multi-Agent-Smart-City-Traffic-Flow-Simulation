"""
Comparative evaluation framework running and contrasting all coordination strategies.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from simulation.engine import SimulationEngine
from evaluation.metrics import PerformanceMetrics, calculate_simulation_metrics
from config import DEFAULT_RANDOM_SEED, DEFAULT_TIME_STEP, SCENARIO_NORMAL


@dataclass
class BenchmarkResult:
    """Holds comparative data across all strategies for a single seed."""
    scenario_name: str
    vehicle_count: int
    seed: int
    metrics_by_strategy: Dict[str, PerformanceMetrics]
    comparison_table: pd.DataFrame
    improvement_table: pd.DataFrame


@dataclass
class MultiSeedBenchmarkResult:
    """Holds aggregated mean and standard deviation across repeated random seeds."""
    scenario_name: str
    vehicle_count: int
    seeds: List[int]
    runs_by_seed: List[BenchmarkResult]
    summary_table: pd.DataFrame


class StrategyComparator:
    """
    Executes benchmark suites comparing Independent routing against coordinated mechanisms
    under strictly identical initial conditions and random seeds.
    """
    STRATEGIES = [
        "Independent",
        "Route Advisories",
        "Congestion Pricing",
        "Dynamic Lanes",
        "Combined"
    ]

    def __init__(self, network_type: str = "smart_city"):
        self.network_type = network_type

    def run_comparison(
        self,
        scenario_name: str = SCENARIO_NORMAL,
        vehicle_count: int = 40,
        max_ticks: int = 150,
        seed: int = DEFAULT_RANDOM_SEED,
        arrival_interval: int = 1
    ) -> BenchmarkResult:
        """
        Runs all 5 strategies under identical seed, arrival schedule, and vehicle assignments.
        """
        metrics_by_strategy: Dict[str, PerformanceMetrics] = {}

        for strat in self.STRATEGIES:
            engine = SimulationEngine(
                network_type=self.network_type,
                max_ticks=max_ticks,
                delta_t=DEFAULT_TIME_STEP
            )
            # Setup with identical seed and scenario parameters
            engine.setup(
                scenario_name=scenario_name,
                vehicle_count=vehicle_count,
                strategy_name=strat,
                seed=seed,
                arrival_interval=arrival_interval
            )
            # Run simulation
            engine.run_to_completion(max_ticks=max_ticks)
            metrics = calculate_simulation_metrics(engine)
            metrics_by_strategy[strat] = metrics

        comparison_df = self._build_comparison_dataframe(metrics_by_strategy)
        improvement_df = self._build_improvement_dataframe(metrics_by_strategy)

        return BenchmarkResult(
            scenario_name=scenario_name,
            vehicle_count=vehicle_count,
            seed=seed,
            metrics_by_strategy=metrics_by_strategy,
            comparison_table=comparison_df,
            improvement_table=improvement_df
        )

    def run_multi_seed_comparison(
        self,
        scenario_name: str = SCENARIO_NORMAL,
        vehicle_count: int = 40,
        max_ticks: int = 150,
        seeds: Optional[List[int]] = None,
        arrival_interval: int = 1
    ) -> MultiSeedBenchmarkResult:
        """
        Runs all 5 strategies across multiple random seeds and reports mean +/- std.
        """
        seed_list = seeds or [42, 101, 202, 303, 404]
        runs: List[BenchmarkResult] = [
            self.run_comparison(scenario_name, vehicle_count, max_ticks, s, arrival_interval)
            for s in seed_list
        ]

        summary_rows = []
        for strat in self.STRATEGIES:
            strat_metrics = [r.metrics_by_strategy[strat] for r in runs]
            comp_rates = [m.completion_rate_pct for m in strat_metrics]
            tt_comp = [m.average_travel_time for m in strat_metrics]
            tt_all = [m.all_departed_avg_time for m in strat_metrics]
            tot_journey = [m.total_travel_time for m in strat_metrics]
            delays = [m.average_delay for m in strat_metrics]
            densities = [m.average_density * 100.0 for m in strat_metrics]
            queues = [m.average_queue_length for m in strat_metrics]

            summary_rows.append({
                "Strategy": strat,
                "Completion %": f"{np.mean(comp_rates):.1f} ± {np.std(comp_rates):.1f}%",
                "Completed Avg Time (s)": f"{np.mean(tt_comp):.1f} ± {np.std(tt_comp):.1f}",
                "All-Departed Avg (s)": f"{np.mean(tt_all):.1f} ± {np.std(tt_all):.1f}",
                "Total Journey Time (s)": f"{np.mean(tot_journey):.0f} ± {np.std(tot_journey):.0f}",
                "Avg Delay (s)": f"{np.mean(delays):.1f} ± {np.std(delays):.1f}",
                "Avg Density (%)": f"{np.mean(densities):.2f} ± {np.std(densities):.2f}%",
                "Avg Queue (veh)": f"{np.mean(queues):.2f} ± {np.std(queues):.2f}"
            })

        return MultiSeedBenchmarkResult(
            scenario_name=scenario_name,
            vehicle_count=vehicle_count,
            seeds=seed_list,
            runs_by_seed=runs,
            summary_table=pd.DataFrame(summary_rows)
        )

    def _build_comparison_dataframe(
        self,
        metrics: Dict[str, PerformanceMetrics]
    ) -> pd.DataFrame:
        """Constructs a consolidated table of the 6 key parameters, clearly distinguishing completed vs unfinished."""
        records = []
        for strat, m in metrics.items():
            records.append({
                "Strategy": strat,
                "Completed": f"{m.throughput}/{m.total_vehicles}",
                "Unfinished": m.unfinished_vehicles,
                "Completion %": f"{m.completion_rate_pct:.1f}%",
                "Avg Travel Time (s)": round(m.average_travel_time, 1),
                "All-Departed Avg (s)": round(m.all_departed_avg_time, 1),
                "Unfinished Elapsed (s)": round(m.unfinished_avg_elapsed_time, 1),
                "Total Journey Time (s)": round(m.total_travel_time, 1),
                "Sim Duration (s)": round(m.simulation_duration_sec, 1),
                "Avg Delay (s)": round(m.average_delay, 1),
                "Avg Density": f"{m.average_density * 100:.1f}%",
                "Peak Density": f"{m.peak_density * 100:.1f}%",
                "Avg Queue (veh)": round(m.average_queue_length, 2),
                "Peak Queue": m.peak_queue_length,
                "Avg Speed (km/h)": round(m.average_speed_kmh, 1)
            })
        return pd.DataFrame(records)

    def _build_improvement_dataframe(
        self,
        metrics: Dict[str, PerformanceMetrics]
    ) -> pd.DataFrame:
        """
        Calculates percentage improvement of each coordinated strategy relative to Independent baseline.
        Positive % indicates an improvement (reduction in delay/travel time/queue or increase in throughput/speed).
        """
        baseline = metrics.get("Independent")
        if not baseline:
            return pd.DataFrame()

        rows = []
        for strat, m in metrics.items():
            if strat == "Independent":
                continue

            # Travel Time Improvement (lower is better)
            if baseline.average_travel_time > 0:
                tt_imp = ((baseline.average_travel_time - m.average_travel_time) / baseline.average_travel_time) * 100.0
            else:
                tt_imp = 0.0

            # Delay Improvement (lower is better)
            if baseline.average_delay > 0:
                delay_imp = ((baseline.average_delay - m.average_delay) / baseline.average_delay) * 100.0
            else:
                delay_imp = 0.0

            # Congestion / Density Improvement (lower is better)
            if baseline.average_density > 0:
                density_imp = ((baseline.average_density - m.average_density) / baseline.average_density) * 100.0
            else:
                density_imp = 0.0

            # Queue Improvement (lower is better)
            if baseline.average_queue_length > 0:
                queue_imp = ((baseline.average_queue_length - m.average_queue_length) / baseline.average_queue_length) * 100.0
            else:
                queue_imp = 0.0

            # Throughput Improvement (higher is better)
            if baseline.throughput > 0:
                tp_imp = ((m.throughput - baseline.throughput) / baseline.throughput) * 100.0
            else:
                tp_imp = 100.0 if m.throughput > 0 else 0.0

            rows.append({
                "Coordinated Strategy": strat,
                "Travel Time Reduction": f"{tt_imp:+.1f}%",
                "Delay Reduction": f"{delay_imp:+.1f}%",
                "Congestion Reduction": f"{density_imp:+.1f}%",
                "Queue Reduction": f"{queue_imp:+.1f}%",
                "Throughput Gain": f"{tp_imp:+.1f}%"
            })

        return pd.DataFrame(rows)
