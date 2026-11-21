"""
Discrete-time Simulation Engine orchestrating vehicles, road network, monitoring, and AI coordination.
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
import copy

from road_network.network import RoadNetwork
from road_network.scenarios import build_smart_city_network, build_arterial_corridor_network
from routing.route_planner import RoutePlanner
from agents.vehicle import VehicleAgent
from agents.vehicle_manager import VehicleManager
from monitoring.traffic_monitor import TrafficMonitor
from coordination.coordinator import AICoordinator
from config import DEFAULT_MAX_TICKS, DEFAULT_TIME_STEP, DEFAULT_RANDOM_SEED, SCENARIO_NORMAL


class SimulationState(str, Enum):
    IDLE = "IDLE"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class SimulationEngine:
    """
    Core discrete-time engine coordinating agents, physical network constraints, and AI systems.
    """
    def __init__(
        self,
        network_type: str = "smart_city",
        max_ticks: int = DEFAULT_MAX_TICKS,
        delta_t: float = DEFAULT_TIME_STEP
    ):
        self.network_type = network_type
        self.max_ticks = max_ticks
        self.delta_t = delta_t
        self.tick: int = 0
        self.state: SimulationState = SimulationState.IDLE
        self.scenario_name: str = SCENARIO_NORMAL
        self.vehicle_count: int = 40
        self.seed: int = DEFAULT_RANDOM_SEED
        self.strategy_name: str = "Independent"
        self.arrival_interval: int = 1

        # Initialize network and submodules
        self.network = self._create_network()
        self.planner = RoutePlanner(self.network)
        self.fleet_manager = VehicleManager(self.network, self.planner)
        self.monitor = TrafficMonitor(self.network)
        self.coordinator = AICoordinator()

    def _create_network(self) -> RoadNetwork:
        if self.network_type == "arterial":
            return build_arterial_corridor_network()
        return build_smart_city_network()

    def setup(
        self,
        scenario_name: str = SCENARIO_NORMAL,
        vehicle_count: int = 40,
        strategy_name: str = "Independent",
        seed: int = DEFAULT_RANDOM_SEED,
        network_type: Optional[str] = None,
        arrival_interval: int = 1
    ) -> None:
        """
        Initializes a reproducible simulation run with identical initial vehicle positions.
        """
        if network_type:
            self.network_type = network_type

        self.scenario_name = scenario_name
        self.vehicle_count = vehicle_count
        self.strategy_name = strategy_name
        self.seed = seed
        self.arrival_interval = arrival_interval
        self.tick = 0

        # Fresh network and reset state
        self.network = self._create_network()
        self.planner = RoutePlanner(self.network)
        self.fleet_manager = VehicleManager(self.network, self.planner)
        self.monitor = TrafficMonitor(self.network)
        self.coordinator = AICoordinator()
        self.coordinator.set_strategy(strategy_name)

        # All strategies start with identical initial routes (free-flow shortest time
        # on the empty network) so that every observed difference stems purely from
        # how each coordination mechanism handles emerging congestion.
        routing_crit = "free_flow"
        include_toll = False

        # Generate fleet with fixed seed and staggered arrivals
        self.fleet_manager.generate_scenario_fleet(
            scenario_name=scenario_name,
            vehicle_count=vehicle_count,
            seed=seed,
            routing_criterion=routing_crit,
            include_toll=include_toll,
            arrival_interval=arrival_interval
        )

        # Record initial monitoring state at tick 0
        self.monitor.update(tick=0, fleet_manager=self.fleet_manager)
        self.state = SimulationState.READY

    def start(self) -> None:
        if self.state in (SimulationState.READY, SimulationState.PAUSED):
            self.state = SimulationState.RUNNING

    def pause(self) -> None:
        if self.state == SimulationState.RUNNING:
            self.state = SimulationState.PAUSED

    def resume(self) -> None:
        if self.state == SimulationState.PAUSED:
            self.state = SimulationState.RUNNING

    def reset(self) -> None:
        self.setup(
            scenario_name=self.scenario_name,
            vehicle_count=self.vehicle_count,
            strategy_name=self.strategy_name,
            seed=self.seed,
            network_type=self.network_type,
            arrival_interval=self.arrival_interval
        )

    def step(self) -> Dict[str, Any]:
        """
        Advances the simulation clock by 1 tick:
        1. Apply AI Coordination.
        2. Advance Vehicles (respecting road capacity).
        3. Update Road Conditions and Telemetry.
        4. Check Termination.
        """
        if self.state not in (SimulationState.RUNNING, SimulationState.READY, SimulationState.PAUSED):
            return {"tick": self.tick, "state": self.state}

        self.tick += 1

        # 1. AI Coordination phase
        coord_res = self.coordinator.step(
            tick=self.tick,
            network=self.network,
            fleet_manager=self.fleet_manager,
            monitor=self.monitor,
            planner=self.planner
        )

        # 2. Vehicle Agent Movement phase
        self.fleet_manager.step_all(delta_t=self.delta_t, current_tick=self.tick)

        # 3. Traffic Monitoring update
        net_snap = self.monitor.update(tick=self.tick, fleet_manager=self.fleet_manager)

        # 4. Check completion
        completed = len(self.fleet_manager.get_completed_vehicles())
        total = len(self.fleet_manager.vehicles)

        if completed >= total or self.tick >= self.max_ticks:
            self.state = SimulationState.COMPLETED

        return {
            "tick": self.tick,
            "state": self.state,
            "active_vehicles": net_snap.active_vehicles,
            "completed_vehicles": completed,
            "queued_vehicles": net_snap.queued_vehicles,
            "avg_speed_kmh": net_snap.average_speed_kmh,
            "avg_density": net_snap.average_density,
            "coordination": coord_res
        }

    def run_to_completion(self, max_ticks: Optional[int] = None) -> Dict[str, Any]:
        """Runs the simulation headlessly until completion or max_ticks."""
        limit = max_ticks or self.max_ticks
        self.start()
        while self.state == SimulationState.RUNNING and self.tick < limit:
            self.step()

        fleet_summary = self.fleet_manager.get_fleet_summary()
        net_summary = self.network.get_network_summary()
        
        return {
            "strategy": self.strategy_name,
            "scenario": self.scenario_name,
            "ticks_elapsed": self.tick,
            "total_vehicles": self.vehicle_count,
            "completed_vehicles": fleet_summary["completed_vehicles"],
            "completion_rate": fleet_summary["completion_rate"],
            "average_travel_time": fleet_summary["average_travel_time"],
            "average_delay": fleet_summary["average_delay"],
            "average_waiting_time": fleet_summary["average_waiting_time"],
            "average_network_density": net_summary["average_density"],
            "total_queued": net_summary["total_queued"]
        }
