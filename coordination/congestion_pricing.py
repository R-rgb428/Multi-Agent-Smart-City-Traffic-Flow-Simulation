"""
Congestion Pricing Coordination Mechanism.
Implements Pigouvian virtual dynamic tolls to balance traffic across network corridors.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import pandas as pd

from road_network.network import RoadNetwork


@dataclass
class PricingEvent:
    """Log record of a dynamic toll adjustment."""
    tick: int
    road_id: str
    corridor: str
    density: float
    previous_toll: float
    new_toll: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "road_id": self.road_id,
            "corridor": self.corridor,
            "density": f"{self.density * 100:.1f}%",
            "previous_toll": f"${self.previous_toll:.2f}",
            "new_toll": f"${self.new_toll:.2f}",
            "reason": self.reason
        }


class CongestionPricingSystem:
    """
    Dynamic Pigouvian pricing system internalizing congestion externalities through virtual costs.
    """
    def __init__(
        self,
        density_threshold: float = 0.65,
        base_multiplier: float = 15.0
    ):
        self.density_threshold = density_threshold
        self.base_multiplier = base_multiplier
        self.events: List[PricingEvent] = []

    def reset(self) -> None:
        self.events.clear()

    def update_tolls(self, tick: int, network: RoadNetwork) -> List[PricingEvent]:
        """
        Calculates and applies virtual congestion tolls across all road segments.
        Toll increases non-linearly when density exceeds threshold.
        """
        new_events: List[PricingEvent] = []

        for road_id, road in network.roads.items():
            prev_toll = road.toll
            density = road.density

            if density > self.density_threshold:
                # Excess density over threshold normalized to (1.0 - threshold)
                excess_ratio = (density - self.density_threshold) / max(0.01, 1.0 - self.density_threshold)
                # Non-linear quadratic pricing
                calculated_toll = self.base_multiplier * (excess_ratio ** 1.8)
                new_toll = round(min(50.0, calculated_toll), 2)
                reason = (
                    f"Demand exceeds {self.density_threshold*100:.0f}% capacity threshold. "
                    f"Dynamic surge pricing applied to incentivize bypass routes."
                )
            else:
                new_toll = 0.0
                reason = "Density within acceptable limits. Zero toll applied."

            # Record event if toll changed meaningfully
            if abs(new_toll - prev_toll) > 0.05:
                event = PricingEvent(
                    tick=tick,
                    road_id=road_id,
                    corridor=f"{road.start_node} -> {road.end_node}",
                    density=density,
                    previous_toll=prev_toll,
                    new_toll=new_toll,
                    reason=reason
                )
                self.events.append(event)
                new_events.append(event)

            road.toll = new_toll

        return new_events

    def to_dataframe(self) -> pd.DataFrame:
        """Returns pricing adjustments as DataFrame."""
        if not self.events:
            return pd.DataFrame()
        return pd.DataFrame([e.to_dict() for e in self.events])
