"""
Interactive Map Visualizer for the Smart City road network and vehicle agents.

Provides:
1. render_live_city_map(): Persistent zero-remount SVG component with static road layer
   and 60fps smooth vehicle position interpolation across simulation ticks.
2. render_city_network_map(): Plotly network figure using grouped constant-order traces
   and uirevision stability for static route inspection and backward compatibility.
"""
from __future__ import annotations
import math
import os
from typing import Any, Dict, List, Optional, Tuple
import plotly.graph_objects as go
import streamlit.components.v1 as components

from road_network.network import RoadNetwork, RoadSegment
from agents.vehicle_manager import VehicleManager
from config import THEME_COLORS

LANE_OFFSET = 16.0
HOVER_SAMPLES = 7
ARROW_LEAD = 16.0

_LIVE_MAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_map_component")
_LIVE_MAP_COMPONENT = components.declare_component("smart_city_live_map", path=_LIVE_MAP_DIR)


def _get_road_color(vehicle_count: int, congestion_level: str) -> str:
    """Muted sand-grey for idle roads, cobalt for active low load, terracotta shades for congestion."""
    if vehicle_count == 0:
        return THEME_COLORS["idle_road"]
    return {
        "LOW": THEME_COLORS["low_congestion"],
        "MODERATE": THEME_COLORS["moderate_congestion"],
        "HIGH": THEME_COLORS["high_congestion"],
    }.get(congestion_level, THEME_COLORS["severe_congestion"])


def _offset_segment(network: RoadNetwork, road: RoadSegment) -> Optional[Tuple[float, float, float, float]]:
    u = network.get_intersection(road.start_node)
    v = network.get_intersection(road.end_node)
    if not u or not v:
        return None
    dx, dy = v.x - u.x, v.y - u.y
    length = math.hypot(dx, dy)
    if length == 0:
        return None
    nx, ny = -dy / length, dx / length
    return (
        u.x + nx * LANE_OFFSET, u.y + ny * LANE_OFFSET,
        v.x + nx * LANE_OFFSET, v.y + ny * LANE_OFFSET,
    )


def _road_hover(road: RoadSegment) -> str:
    state = "Idle" if road.vehicle_count == 0 else road.congestion_level.title()
    lane_note = f" (base {road.base_lanes})" if road.current_lanes != road.base_lanes else ""
    return (
        f"<b>{road.road_id}</b>  {road.start_node} &rarr; {road.end_node}<br>"
        f"Condition: <b>{state}</b> · Occupancy: <b>{road.density*100:.0f}%</b><br>"
        f"Vehicles: <b>{road.vehicle_count} / {road.capacity}</b> · Lanes: {road.current_lanes}{lane_note}<br>"
        f"Speed: {road.current_speed*3.6:.0f} / {road.free_flow_speed*3.6:.0f} km/h · Est. {road.estimated_travel_time:.0f} s<br>"
        f"Queue: {road.queue_length} waiting · Toll: ${road.toll:.2f}"
    )


def _heading_degrees(dx: float, dy: float) -> float:
    return math.degrees(math.atan2(dx, dy))


def render_live_city_map(
    network: RoadNetwork,
    fleet_manager: Optional[VehicleManager] = None,
    tick: int = 0,
    show_road_labels: bool = True,
    height: int = 390,
    key: str = "live_city_map",
) -> None:
    """
    Renders the zero-remount persistent SVG city map component.
    Roads and nodes are drawn once per topology; updates stream only changing states
    while vehicles smoothly interpolate between positions.
    """
    nodes_payload: List[Dict[str, Any]] = [
        {
            "id": nid,
            "name": node.name,
            "x": float(node.x),
            "y": float(node.y),
            "connected": len(node.connected_roads),
        }
        for nid, node in network.nodes.items()
    ]

    roads_payload: List[Dict[str, Any]] = []
    for road_id, road in network.roads.items():
        color = _get_road_color(road.vehicle_count, road.congestion_level)
        width = round((3.4 + road.current_lanes * 1.05) if road.vehicle_count > 0 else 2.6, 2)
        roads_payload.append({
            "id": road_id,
            "from": road.start_node,
            "to": road.end_node,
            "color": color,
            "width": width,
            "label": f"{road.vehicle_count}/{road.capacity}" if road.vehicle_count > 0 else "",
            "hover": _road_hover(road),
            "isAlert": road.congestion_level in ("HIGH", "SEVERE"),
        })

    vehicles_payload: List[Dict[str, Any]] = []
    if fleet_manager:
        for v in fleet_manager.vehicles.values():
            if v.completion_status not in ("EN_ROUTE", "WAITING"):
                continue
            is_waiting = v.completion_status == "WAITING"
            road = network.get_road(v.current_road_id) if v.current_road_id else None
            ratio = min(1.0, max(0.0, v.progress_distance / max(1.0, road.length))) if road else 0.0
            hover = (
                f"<b>{v.vehicle_id}</b> · {'Queued' if is_waiting else 'Moving'}<br>"
                f"Trip: {v.origin} &rarr; {v.destination}<br>"
                f"On: {v.current_road_id or 'intersection ' + v.current_node} · Next: {v.target_node or '-'}<br>"
                f"Speed: {v.current_speed*3.6:.0f} km/h · Travel: {v.travel_time:.0f} s · Waiting: {v.waiting_time:.0f} s"
            )
            vehicles_payload.append({
                "id": v.vehicle_id,
                "roadId": v.current_road_id if road else None,
                "progress": round(ratio, 4),
                "nodeId": v.current_node,
                "nextNodeId": v.target_node,
                "waiting": is_waiting,
                "hover": hover,
            })

    topo_sig = f"{network.name}:{len(nodes_payload)}:{len(roads_payload)}:{height}"
    _LIVE_MAP_COMPONENT(
        topoSig=topo_sig,
        tick=int(tick),
        height=int(height),
        showRoadLabels=bool(show_road_labels),
        nodes=nodes_payload,
        roads=roads_payload,
        vehicles=vehicles_payload,
        key=key,
        default=None,
    )


def render_city_network_map(
    network: RoadNetwork,
    fleet_manager: Optional[VehicleManager] = None,
    highlight_road_ids: Optional[List[str]] = None,
    show_road_labels: bool = True,
    height: int = 390
) -> go.Figure:
    """
    Renders the interactive Plotly city network map with grouped constant-order traces
    and uirevision stability under the Sand × Terracotta × Cobalt palette.
    """
    fig = go.Figure()
    highlight_set = set(highlight_road_ids or [])

    # 1A. Combined road drop-shadows (single multi-segment trace with None breaks)
    sh_x: List[Optional[float]] = []
    sh_y: List[Optional[float]] = []

    buckets: Dict[str, Dict[str, Any]] = {
        "IDLE": {"color": THEME_COLORS["idle_road"], "width": 2.6, "x": [], "y": [], "hover": []},
        "LOW": {"color": THEME_COLORS["low_congestion"], "width": 4.8, "x": [], "y": [], "hover": []},
        "MODERATE": {"color": THEME_COLORS["moderate_congestion"], "width": 5.4, "x": [], "y": [], "hover": []},
        "HIGH": {"color": THEME_COLORS["high_congestion"], "width": 5.8, "x": [], "y": [], "hover": []},
        "SEVERE": {"color": THEME_COLORS["severe_congestion"], "width": 6.4, "x": [], "y": [], "hover": []},
    }
    hl_x: List[Optional[float]] = []
    hl_y: List[Optional[float]] = []
    hl_hover: List[str] = []
    lbl_x: List[float] = []
    lbl_y: List[float] = []
    lbl_txt: List[str] = []

    for road_id, road in network.roads.items():
        seg = _offset_segment(network, road)
        if seg is None:
            continue
        x0, y0, x1, y1 = seg
        sh_x.extend([x0 + 3.5, x1 + 3.5, None])
        sh_y.extend([y0 - 5.0, y1 - 5.0, None])

        xs = [x0 + (x1 - x0) * i / (HOVER_SAMPLES - 1) for i in range(HOVER_SAMPLES)]
        ys = [y0 + (y1 - y0) * i / (HOVER_SAMPLES - 1) for i in range(HOVER_SAMPLES)]
        hover = _road_hover(road)

        if road_id in highlight_set:
            hl_x.extend(xs + [None])
            hl_y.extend(ys + [None])
            hl_hover.extend([hover] * HOVER_SAMPLES + [""])
        else:
            bkey = "IDLE" if road.vehicle_count == 0 else road.congestion_level
            b = buckets.get(bkey, buckets["SEVERE"])
            b["x"].extend(xs + [None])
            b["y"].extend(ys + [None])
            b["hover"].extend([hover] * HOVER_SAMPLES + [""])

        if show_road_labels and road.vehicle_count > 0:
            lbl_x.append(x0 + 0.5 * (x1 - x0))
            lbl_y.append(y0 + 0.5 * (y1 - y0))
            lbl_txt.append(f"{road.vehicle_count}/{road.capacity}")

    fig.add_trace(go.Scatter(
        x=sh_x or [None], y=sh_y or [None],
        mode="lines",
        line=dict(color="rgba(31, 61, 58, 0.09)", width=7.0),
        hoverinfo="skip", showlegend=False
    ))

    # 1B. Fixed-order road congestion traces
    for bkey in ("IDLE", "LOW", "MODERATE", "HIGH", "SEVERE"):
        b = buckets[bkey]
        fig.add_trace(go.Scatter(
            x=b["x"] or [None], y=b["y"] or [None],
            mode="lines+markers",
            line=dict(color=b["color"], width=b["width"]),
            marker=dict(size=b["width"] + 6, color="rgba(0,0,0,0)"),
            hoverinfo="text" if b["hover"] else "skip",
            hovertext=b["hover"] or None,
            showlegend=False
        ))

    # Highlighted route trace (always emitted to maintain fixed trace count)
    fig.add_trace(go.Scatter(
        x=hl_x or [None], y=hl_y or [None],
        mode="lines+markers",
        line=dict(color=THEME_COLORS["primary_dark"], width=6.2),
        marker=dict(size=12, color="rgba(0,0,0,0)"),
        hoverinfo="text" if hl_hover else "skip",
        hovertext=hl_hover or None,
        showlegend=False
    ))

    # Road load labels trace (always emitted)
    fig.add_trace(go.Scatter(
        x=lbl_x or [None], y=lbl_y or [None],
        mode="text",
        text=lbl_txt or None,
        textfont=dict(color=THEME_COLORS["text_secondary"], size=9, family="Inter, sans-serif"),
        hoverinfo="skip", showlegend=False
    ))

    # 2. Intersections
    xs_all = [n.x for n in network.nodes.values()] or [0.0]
    ys_all = [n.y for n in network.nodes.values()] or [0.0]
    min_x, max_x, min_y, max_y = min(xs_all), max(xs_all), min(ys_all), max(ys_all)
    mid_x = (min_x + max_x) / 2.0

    node_x, node_y, node_hover = [], [], []
    for node_id, node in network.nodes.items():
        node_x.append(node.x)
        node_y.append(node.y)
        node_hover.append(f"<b>{node.name}</b> ({node_id})<br>Connected segments: {len(node.connected_roads)}")

        if node.y >= max_y - 60:
            xshift, yshift = 0, 22
        elif node.y <= min_y + 60:
            xshift, yshift = 0, -22
        elif node.x <= min_x + 80:
            xshift, yshift = -46, 0
        elif node.x >= max_x - 80:
            xshift, yshift = 46, 0
        else:
            xshift, yshift = (28 if node.x >= mid_x else -28), 18

        fig.add_annotation(
            x=node.x, y=node.y, text=f"<b>{node_id}</b>",
            showarrow=False, xshift=xshift, yshift=yshift,
            bgcolor="rgba(217, 237, 229, 0.94)", bordercolor=THEME_COLORS["border"],
            borderwidth=1, borderpad=3.5,
            font=dict(color=THEME_COLORS["text_primary"], size=10.5, family="Inter, sans-serif")
        )

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        marker=dict(size=16, color=THEME_COLORS["node_color"], line=dict(color=THEME_COLORS["node_border"], width=2.3)),
        hoverinfo="text", hovertext=node_hover,
        showlegend=False
    ))

    # 3. Vehicles (constant-order traces)
    moving_x, moving_y, moving_hover = [], [], []
    queued_x, queued_y, queued_hover = [], [], []
    arrow_x, arrow_y, arrow_angle, arrow_color = [], [], [], []

    if fleet_manager:
        for v in fleet_manager.vehicles.values():
            if v.completion_status not in ("EN_ROUTE", "WAITING"):
                continue

            road = network.get_road(v.current_road_id) if v.current_road_id else None
            seg = _offset_segment(network, road) if road else None

            if seg is not None:
                x0, y0, x1, y1 = seg
                ratio = min(1.0, max(0.0, v.progress_distance / max(1.0, road.length)))
                vx, vy = x0 + ratio * (x1 - x0), y0 + ratio * (y1 - y0)
                hdx, hdy = x1 - x0, y1 - y0
            else:
                node = network.get_intersection(v.current_node)
                if not node:
                    continue
                vx, vy = node.x, node.y
                target = network.get_intersection(v.target_node) if v.target_node else None
                hdx, hdy = (target.x - vx, target.y - vy) if target else (0.0, 0.0)

            is_waiting = v.completion_status == "WAITING"
            hover = (
                f"<b>{v.vehicle_id}</b> · {'Queued' if is_waiting else 'Moving'}<br>"
                f"Trip: {v.origin} &rarr; {v.destination}<br>"
                f"On: {v.current_road_id or 'intersection ' + v.current_node} · Next: {v.target_node or '-'}<br>"
                f"Speed: {v.current_speed*3.6:.0f} km/h · Travel: {v.travel_time:.0f} s · Waiting: {v.waiting_time:.0f} s"
            )
            if is_waiting:
                queued_x.append(vx); queued_y.append(vy); queued_hover.append(hover)
            else:
                moving_x.append(vx); moving_y.append(vy); moving_hover.append(hover)

            norm = math.hypot(hdx, hdy)
            if norm > 0:
                arrow_x.append(vx + hdx / norm * ARROW_LEAD)
                arrow_y.append(vy + hdy / norm * ARROW_LEAD)
                arrow_angle.append(_heading_degrees(hdx, hdy))
                arrow_color.append(THEME_COLORS["vehicle_waiting"] if is_waiting else THEME_COLORS["vehicle_en_route"])

    fig.add_trace(go.Scatter(
        x=arrow_x or [None], y=arrow_y or [None],
        mode="markers",
        marker=dict(symbol="triangle-up", size=7, angle=arrow_angle or [0], color=arrow_color or THEME_COLORS["vehicle_en_route"]),
        hoverinfo="skip", showlegend=False
    ))

    for xs, ys, hovers, color, halo_color, name in [
        (moving_x, moving_y, moving_hover, THEME_COLORS["vehicle_en_route"], THEME_COLORS["accent_primary"], "Moving"),
        (queued_x, queued_y, queued_hover, THEME_COLORS["vehicle_waiting"], THEME_COLORS["accent_muted"], "Queued"),
    ]:
        fig.add_trace(go.Scatter(
            x=xs or [None], y=ys or [None],
            mode="markers",
            marker=dict(symbol="circle", size=18, color=halo_color, opacity=0.25, line=dict(width=0)),
            hoverinfo="skip",
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=xs or [None], y=ys or [None],
            mode="markers",
            marker=dict(symbol="circle", size=9.5, color=color, line=dict(color=THEME_COLORS["card_bg"], width=1.7)),
            hoverinfo="text" if hovers else "skip",
            hovertext=hovers or None,
            name=name
        ))

    # 4. Road condition legend inside map corner
    for label, col in [
        ("Idle", THEME_COLORS["idle_road"]),
        ("Low", THEME_COLORS["low_congestion"]),
        ("Moderate", THEME_COLORS["moderate_congestion"]),
        ("High", THEME_COLORS["high_congestion"]),
        ("Severe", THEME_COLORS["severe_congestion"]),
    ]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=col, width=3.5), name=label))

    fig.update_layout(
        template="plotly_white",
        uirevision="smart_city_map_v1",
        height=height,
        plot_bgcolor=THEME_COLORS["card_bg"],
        paper_bgcolor=THEME_COLORS["card_bg"],
        font=dict(color=THEME_COLORS["text_primary"], family="Inter, sans-serif"),
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="closest",
        xaxis=dict(range=[min_x - 210, max_x + 190], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[min_y - 110, max_y + 130], showgrid=False, zeroline=False,
                   showticklabels=False, scaleanchor="x", scaleratio=1),
        legend=dict(
            x=0.01, y=0.99, xanchor="left", yanchor="top",
            bgcolor="rgba(237, 246, 243, 0.94)",
            bordercolor=THEME_COLORS["border"],
            borderwidth=1,
            font=dict(color=THEME_COLORS["text_secondary"], size=10.5)
        ),
        hoverlabel=dict(
            bgcolor=THEME_COLORS["card_bg"], bordercolor=THEME_COLORS["border"],
            font=dict(color=THEME_COLORS["text_primary"], size=12, family="Inter, sans-serif")
        )
    )
    return fig
