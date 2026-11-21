"""
Calculation of the 6 core traffic performance metrics specified in the project report.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np

from simulation.engine import SimulationEngine


@dataclass
class PerformanceMetrics:
    """Encapsulates the 6 standard performance metrics."""
    # 1. Average Travel Time (seconds)
    average_travel_time: float
    # 2. Total Travel Time (seconds)
    total_travel_time: float
    # 3. Traffic Congestion (mean network density 0.0 - 1.0)
    average_density: float
    peak_density: float
    # 4. Queue Length (vehicles)
    average_queue_length: float
    peak_queue_length: int
    # 5. Throughput (completed vehicles and completion percentage)
    throughput: int
    completion_rate_pct: float
    # 6. Average Delay (seconds over free-flow)
    average_delay: float
    total_delay: float

    # Additional supporting indicators (completed vs unfinished & simulation time)
    total_vehicles: int
    active_vehicles: int
    unfinished_vehicles: int
    unfinished_avg_elapsed_time: float
    unfinished_total_elapsed_time: float
    all_departed_avg_time: float
    simulation_ticks: int
    simulation_duration_sec: float
    average_speed_kmh: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Completed Avg Travel Time (s)": round(self.average_travel_time, 1),
            "All-Departed Avg Time (s)": round(self.all_departed_avg_time, 1),
            "Unfinished Avg Elapsed (s)": round(self.unfinished_avg_elapsed_time, 1),
            "Total Journey Time (s)": round(self.total_travel_time, 1),
            "Simulation Elapsed Time (s)": round(self.simulation_duration_sec, 1),
            "Traffic Congestion (Density)": f"{self.average_density * 100:.1f}%",
            "Peak Congestion (Density)": f"{self.peak_density * 100:.1f}%",
            "Average Queue Length": round(self.average_queue_length, 2),
            "Peak Queue Length": self.peak_queue_length,
            "Throughput (Completed)": f"{self.throughput} / {self.total_vehicles} ({self.completion_rate_pct:.1f}%)",
            "Unfinished Vehicles": self.unfinished_vehicles,
            "Average Delay (s)": round(self.average_delay, 1),
            "Total Delay (s)": round(self.total_delay, 1),
            "Average Speed (km/h)": round(self.average_speed_kmh, 1)
        }


def calculate_simulation_metrics(engine: SimulationEngine) -> PerformanceMetrics:
    """
    Computes all 6 performance evaluation parameters from an actual simulation instance.
    """
    fleet = list(engine.fleet_manager.vehicles.values())
    completed = [v for v in fleet if v.completion_status == "COMPLETED"]
    unfinished = [v for v in fleet if v.completion_status != "COMPLETED"]
    departed_unfinished = [v for v in unfinished if v.travel_time > 0]
    all_departed = [v for v in fleet if v.travel_time > 0 or v.completion_status == "COMPLETED"]
    total_vehicles = len(fleet)

    # 1. Average Travel Time (completed only, plus all-departed & unfinished elapsed)
    avg_travel_time = float(np.mean([v.travel_time for v in completed])) if completed else 0.0
    unfinished_avg_elapsed = float(np.mean([v.travel_time for v in departed_unfinished])) if departed_unfinished else 0.0
    unfinished_total_elapsed = float(sum(v.travel_time for v in unfinished))
    all_departed_avg = float(np.mean([v.travel_time for v in all_departed])) if all_departed else 0.0

    # 2. Total Journey Time (combined vehicle travel time) vs Simulation Duration
    total_travel_time = float(sum(v.travel_time for v in fleet))
    simulation_duration_sec = float(engine.tick * engine.delta_t)

    # 3. Traffic Congestion from monitoring history
    history = engine.monitor.history
    if history:
        densities = [h.average_density for h in history]
        avg_density = float(np.mean(densities))
        peak_density = float(np.max(densities))
        
        # 4. Queue Length from history
        queues = [h.queued_vehicles for h in history]
        avg_queue = float(np.mean(queues))
        peak_queue = int(np.max(queues))
        
        speeds = [h.average_speed_kmh for h in history]
        avg_speed = float(np.mean(speeds))
    else:
        # Fallback to current network snapshot
        net_summary = engine.network.get_network_summary()
        avg_density = float(net_summary["average_density"])
        peak_density = avg_density
        avg_queue = float(net_summary["total_queued"])
        peak_queue = int(net_summary["total_queued"])
        avg_speed = 0.0

    # 5. Throughput
    throughput = len(completed)
    completion_rate = (throughput / max(1, total_vehicles)) * 100.0

    # 6. Average Delay compared to free-flow baseline
    if completed:
        delays = [max(0.0, v.travel_time - v.free_flow_travel_time) for v in completed]
        avg_delay = float(np.mean(delays))
    else:
        avg_delay = 0.0

    total_delay = float(sum(max(0.0, v.travel_time - v.free_flow_travel_time) for v in fleet))
    active_count = len(engine.fleet_manager.get_active_vehicles())

    return PerformanceMetrics(
        average_travel_time=avg_travel_time,
        total_travel_time=total_travel_time,
        average_density=avg_density,
        peak_density=peak_density,
        average_queue_length=avg_queue,
        peak_queue_length=peak_queue,
        throughput=throughput,
        completion_rate_pct=completion_rate,
        average_delay=avg_delay,
        total_delay=total_delay,
        total_vehicles=total_vehicles,
        active_vehicles=active_count,
        unfinished_vehicles=len(unfinished),
        unfinished_avg_elapsed_time=unfinished_avg_elapsed,
        unfinished_total_elapsed_time=unfinished_total_elapsed,
        all_departed_avg_time=all_departed_avg,
        simulation_ticks=engine.tick,
        simulation_duration_sec=simulation_duration_sec,
        average_speed_kmh=avg_speed
    )
