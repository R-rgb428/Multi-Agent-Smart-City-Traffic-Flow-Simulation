"""
Dynamic Lane Assignment Coordination Mechanism.
Dynamically borrows reversible lanes between opposing directions during asymmetric flow surges.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd

from road_network.network import RoadNetwork, RoadSegment


@dataclass
class LaneAdjustmentEvent:
    """Log record of a dynamic reversible lane reallocation."""
    tick: int
    corridor: str
    road_id_forward: str
    road_id_reverse: str
    forward_lanes: int
    reverse_lanes: int
    forward_demand: int
    reverse_demand: int
    ratio: float
    action: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "corridor": self.corridor,
            "forward_road": self.road_id_forward,
            "reverse_road": self.road_id_reverse,
            "forward_lanes": self.forward_lanes,
            "reverse_lanes": self.reverse_lanes,
            "forward_demand": self.forward_demand,
            "reverse_demand": self.reverse_demand,
            "demand_ratio": f"{self.ratio:.2f}:1",
            "action": self.action,
            "reason": self.reason
        }


class DynamicLaneAssignmentSystem:
    """
    Intelligent reversible lane controller optimizing directional throughput.
    Preserves total bidirectional road capacity while adapting to asymmetric surges.
    """
    def __init__(
        self,
        ratio_threshold: float = 1.75,
        rebalance_interval: int = 10
    ):
        self.ratio_threshold = ratio_threshold
        self.rebalance_interval = rebalance_interval
        self.events: List[LaneAdjustmentEvent] = []
        self._last_adjustment_tick: Dict[str, int] = {}

    def reset(self) -> None:
        self.events.clear()
        self._last_adjustment_tick.clear()

    def evaluate_and_reallocate(self, tick: int, network: RoadNetwork) -> List[LaneAdjustmentEvent]:
        """
        Scans paired bidirectional road segments and shifts lanes if demand is heavily unbalanced.
        """
        new_events: List[LaneAdjustmentEvent] = []
        processed_pairs = set()

        for road_id, road in network.roads.items():
            paired_id = road.paired_road_id
            if not paired_id:
                continue

            pair_key = tuple(sorted([road_id, paired_id]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)

            paired_road = network.get_road(paired_id)
            if not paired_road:
                continue

            # Respect rebalance interval
            corridor_key = f"{road_id}<->{paired_id}"
            if (tick - self._last_adjustment_tick.get(corridor_key, -999)) < self.rebalance_interval:
                continue

            # Total lane invariant
            total_lanes = road.base_lanes + paired_road.base_lanes

            # Directional demand: active vehicles + queue
            demand_fwd = road.vehicle_count + road.queue_length
            demand_rev = paired_road.vehicle_count + paired_road.queue_length

            # Ratio calculation with Laplace smoothing
            ratio_fwd = (demand_fwd + 1.0) / (demand_rev + 1.0)
            ratio_rev = (demand_rev + 1.0) / (demand_fwd + 1.0)

            action = "MAINTAIN"
            reason = "Demand balanced across both directions."

            # Case A: Heavy forward surge
            if ratio_fwd >= self.ratio_threshold and paired_road.current_lanes > 1:
                if road.current_lanes < total_lanes - 1:
                    road.current_lanes += 1
                    paired_road.current_lanes -= 1
                    action = f"SHIFT_TO_FORWARD ({road.current_lanes} : {paired_road.current_lanes})"
                    reason = (
                        f"Inbound demand surge ({demand_fwd} vs {demand_rev}, ratio {ratio_fwd:.2f}:1). "
                        f"Allocated +1 reversible lane to {road_id} (total {road.current_lanes} lanes, capacity {road.capacity})."
                    )
                    self._last_adjustment_tick[corridor_key] = tick

            # Case B: Heavy reverse surge
            elif ratio_rev >= self.ratio_threshold and road.current_lanes > 1:
                if paired_road.current_lanes < total_lanes - 1:
                    paired_road.current_lanes += 1
                    road.current_lanes -= 1
                    action = f"SHIFT_TO_REVERSE ({road.current_lanes} : {paired_road.current_lanes})"
                    reason = (
                        f"Outbound demand surge ({demand_rev} vs {demand_fwd}, ratio {ratio_rev:.2f}:1). "
                        f"Allocated +1 reversible lane to {paired_id} (total {paired_road.current_lanes} lanes, capacity {paired_road.capacity})."
                    )
                    self._last_adjustment_tick[corridor_key] = tick

            # Case C: Rebalance back to base configuration if traffic normalized
            elif (0.75 <= ratio_fwd <= 1.35) and (road.current_lanes != road.base_lanes):
                road.current_lanes = road.base_lanes
                paired_road.current_lanes = paired_road.base_lanes
                action = f"RESTORE_BASE ({road.current_lanes} : {paired_road.current_lanes})"
                reason = "Demand normalized. Restored default symmetrical lane layout."
                self._last_adjustment_tick[corridor_key] = tick

            if action != "MAINTAIN":
                event = LaneAdjustmentEvent(
                    tick=tick,
                    corridor=f"{road.start_node} <-> {road.end_node}",
                    road_id_forward=road_id,
                    road_id_reverse=paired_id,
                    forward_lanes=road.current_lanes,
                    reverse_lanes=paired_road.current_lanes,
                    forward_demand=demand_fwd,
                    reverse_demand=demand_rev,
                    ratio=max(ratio_fwd, ratio_rev),
                    action=action,
                    reason=reason
                )
                self.events.append(event)
                new_events.append(event)

        return new_events

    def to_dataframe(self) -> pd.DataFrame:
        """Returns log of dynamic lane shifts."""
        if not self.events:
            return pd.DataFrame()
        return pd.DataFrame([e.to_dict() for e in self.events])
