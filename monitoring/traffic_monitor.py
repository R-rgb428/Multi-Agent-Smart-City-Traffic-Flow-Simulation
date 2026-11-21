"""
Traffic Monitor component tracking real-time road conditions and network metrics.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import pandas as pd

from road_network.network import RoadNetwork, RoadSegment
from config import THEME_COLORS, CONGESTION_LEVELS


@dataclass
class RoadConditionSnapshot:
    """Detailed observation snapshot for a single road segment."""
    road_id: str
    start_node: str
    end_node: str
    vehicle_count: int
    capacity: int
    density: float
    current_speed: float              # m/s
    speed_kmh: float                  # km/h
    free_flow_speed: float            # m/s
    estimated_travel_time: float      # seconds
    queue_length: int
    congestion_level: str             # LOW, MODERATE, HIGH, SEVERE
    color: str                        # Hex color for dashboard rendering
    toll: float
    current_lanes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "road_id": self.road_id,
            "corridor": f"{self.start_node} -> {self.end_node}",
            "vehicles": self.vehicle_count,
            "capacity": self.capacity,
            "density": f"{self.density * 100:.1f}%",
            "speed_kmh": round(self.speed_kmh, 1),
            "travel_time_sec": round(self.estimated_travel_time, 1),
            "queue": self.queue_length,
            "congestion": self.congestion_level,
            "toll": round(self.toll, 2),
            "lanes": self.current_lanes
        }


@dataclass
class NetworkMetricsSnapshot:
    """Aggregate network state at a discrete simulation tick."""
    tick: int
    total_vehicles: int
    active_vehicles: int
    completed_vehicles: int
    queued_vehicles: int
    average_density: float
    average_speed_kmh: float
    severe_roads_count: int
    high_roads_count: int
    total_system_delay: float
    bottlenecks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "total_vehicles": self.total_vehicles,
            "active_vehicles": self.active_vehicles,
            "completed_vehicles": self.completed_vehicles,
            "queued_vehicles": self.queued_vehicles,
            "average_density": round(self.average_density, 3),
            "average_speed_kmh": round(self.average_speed_kmh, 1),
            "severe_roads_count": self.severe_roads_count,
            "high_roads_count": self.high_roads_count,
            "total_system_delay": round(self.total_system_delay, 1),
            "bottlenecks": ", ".join(self.bottlenecks)
        }


class TrafficMonitor:
    """
    Continuous observer monitoring road segments and producing real-time telemetry.
    """
    def __init__(self, network: RoadNetwork):
        self.network = network
        self.history: List[NetworkMetricsSnapshot] = []
        self._current_snapshots: Dict[str, RoadConditionSnapshot] = {}

    def get_color_for_level(self, level: str) -> str:
        """Maps congestion level to UI palette color."""
        if level == "LOW":
            return THEME_COLORS["low_congestion"]
        elif level == "MODERATE":
            return THEME_COLORS["moderate_congestion"]
        elif level == "HIGH":
            return THEME_COLORS["high_congestion"]
        else:
            return THEME_COLORS["severe_congestion"]

    def update(self, tick: int, fleet_manager: Any) -> NetworkMetricsSnapshot:
        """
        Polls network and fleet to produce fresh telemetry snapshot.
        """
        self._current_snapshots.clear()
        severe_count = 0
        high_count = 0
        total_density = 0.0
        total_speeds = 0.0
        bottleneck_candidates: List[Tuple[float, str]] = []

        for road_id, road in self.network.roads.items():
            level = road.congestion_level
            color = self.get_color_for_level(level)

            if level == "SEVERE":
                severe_count += 1
            elif level == "HIGH":
                high_count += 1

            total_density += road.density
            total_speeds += road.current_speed

            if road.density >= CONGESTION_LEVELS["HIGH"]:
                bottleneck_candidates.append((road.density, road_id))

            snapshot = RoadConditionSnapshot(
                road_id=road.road_id,
                start_node=road.start_node,
                end_node=road.end_node,
                vehicle_count=road.vehicle_count,
                capacity=road.capacity,
                density=road.density,
                current_speed=road.current_speed,
                speed_kmh=road.current_speed * 3.6,
                free_flow_speed=road.free_flow_speed,
                estimated_travel_time=road.estimated_travel_time,
                queue_length=road.queue_length,
                congestion_level=level,
                color=color,
                toll=road.toll,
                current_lanes=road.current_lanes
            )
            self._current_snapshots[road_id] = snapshot

        # Sort bottlenecks by density descending
        bottleneck_candidates.sort(reverse=True, key=lambda x: x[0])
        top_bottlenecks = [b[1] for b in bottleneck_candidates[:4]]

        num_roads = max(1, len(self.network.roads))
        avg_density = total_density / num_roads
        avg_speed_kmh = (total_speeds / num_roads) * 3.6

        # Fleet metrics
        active = len(fleet_manager.get_active_vehicles())
        completed = len(fleet_manager.get_completed_vehicles())
        queued = len(fleet_manager.get_waiting_vehicles())
        total_vehicles = len(fleet_manager.vehicles)

        total_delay = sum(
            max(0.0, v.travel_time - v.free_flow_travel_time)
            for v in fleet_manager.vehicles.values()
        )

        net_snap = NetworkMetricsSnapshot(
            tick=tick,
            total_vehicles=total_vehicles,
            active_vehicles=active,
            completed_vehicles=completed,
            queued_vehicles=queued,
            average_density=avg_density,
            average_speed_kmh=avg_speed_kmh,
            severe_roads_count=severe_count,
            high_roads_count=high_count,
            total_system_delay=total_delay,
            bottlenecks=top_bottlenecks
        )
        self.history.append(net_snap)
        return net_snap

    def get_road_snapshot(self, road_id: str) -> Optional[RoadConditionSnapshot]:
        return self._current_snapshots.get(road_id)

    def get_all_road_snapshots(self) -> List[RoadConditionSnapshot]:
        return list(self._current_snapshots.values())

    def get_congested_roads(self, min_level: str = "HIGH") -> List[RoadConditionSnapshot]:
        """Returns road segments currently marked at or above min_level."""
        qualifying = ["HIGH", "SEVERE"] if min_level == "HIGH" else ["MODERATE", "HIGH", "SEVERE"]
        return [s for s in self._current_snapshots.values() if s.congestion_level in qualifying]

    def reset(self) -> None:
        """Clears monitoring history."""
        self.history.clear()
        self._current_snapshots.clear()

    def roads_to_dataframe(self) -> pd.DataFrame:
        """Tabular summary of all roads."""
        return pd.DataFrame([s.to_dict() for s in self._current_snapshots.values()])

    def history_to_dataframe(self) -> pd.DataFrame:
        """Time-series DataFrame of simulation history."""
        return pd.DataFrame([h.to_dict() for h in self.history])
