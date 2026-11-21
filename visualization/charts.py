"""
Analytical charting components styled for the Mint Mist light theme.
"""
from __future__ import annotations
import json
import math
import os
import shutil
from typing import Dict, Optional
import pandas as pd
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.utils import PlotlyJSONEncoder
import streamlit.components.v1 as components

from config import THEME_COLORS
from evaluation.metrics import PerformanceMetrics

_LIVE_TELEMETRY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_telemetry_component")
_PLOTLY_JS_DST = os.path.join(_LIVE_TELEMETRY_DIR, "plotly.min.js")
if not os.path.exists(_PLOTLY_JS_DST):
    _plotly_src = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
    if os.path.exists(_plotly_src):
        os.makedirs(_LIVE_TELEMETRY_DIR, exist_ok=True)
        shutil.copyfile(_plotly_src, _PLOTLY_JS_DST)

_LIVE_TELEMETRY_COMPONENT = components.declare_component("smart_city_live_telemetry", path=_LIVE_TELEMETRY_DIR)

BG_SURFACE = THEME_COLORS["card_bg"]
GRID_COLOR = "#E4EEEA"
AXIS_LINE = THEME_COLORS["border"]
TEXT_PRIMARY = THEME_COLORS["text_primary"]
TEXT_SECONDARY = THEME_COLORS["text_secondary"]
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"


def _apply_soft_layout(fig: go.Figure, title: str = "", height: int = 280) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        uirevision="telemetry_chart_v1",
        title=dict(text=title, x=0.01, xanchor="left", y=0.96, yanchor="top", font=dict(size=13.5, color=TEXT_PRIMARY, family=FONT_FAMILY)),
        height=height,
        plot_bgcolor=BG_SURFACE,
        paper_bgcolor=BG_SURFACE,
        font=dict(color=TEXT_PRIMARY, size=12, family=FONT_FAMILY),
        margin=dict(l=42, r=18, t=54, b=38),
        xaxis=dict(gridcolor=GRID_COLOR, linecolor=AXIS_LINE, tickfont=dict(color=TEXT_SECONDARY, size=11)),
        yaxis=dict(gridcolor=GRID_COLOR, linecolor=AXIS_LINE, tickfont=dict(color=TEXT_SECONDARY, size=11)),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1.0,
            font=dict(color=TEXT_SECONDARY, size=11)
        )
    )
    return fig


def _empty_soft_figure(message: str, title: str = "", height: int = 260) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(color=TEXT_SECONDARY, size=13, family=FONT_FAMILY))
    fig.update_layout(
        template="plotly_white",
        uirevision="telemetry_chart_v1",
        title=dict(text=title, font=dict(size=14, color=TEXT_PRIMARY, family=FONT_FAMILY)),
        height=height,
        plot_bgcolor=BG_SURFACE,
        paper_bgcolor=BG_SURFACE,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def render_live_telemetry_chart(fig: go.Figure, height: int = 240, key: str = "live_telemetry") -> None:
    """Renders a Plotly figure inside a persistent iframe that appends traces in-place via Plotly.extendTraces."""
    spec = json.loads(json.dumps(fig.to_plotly_json(), cls=PlotlyJSONEncoder))
    _LIVE_TELEMETRY_COMPONENT(
        spec=spec,
        height=int(height),
        chartKey=key,
        key=key,
        default=None,
    )


def render_metrics_timeline(
    history_df: pd.DataFrame,
    x_max: Optional[int] = None,
    y_max: Optional[float] = None,
) -> go.Figure:
    """Renders multi-trace chart showing fleet state and completion progression over ticks."""
    if history_df.empty:
        return _empty_soft_figure("Advance simulation to view fleet progression.", "Fleet Progression", height=290)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history_df["tick"].tolist(),
        y=history_df["active_vehicles"].tolist(),
        mode="lines",
        name="Active",
        line=dict(color=THEME_COLORS["accent_muted"], width=2.2)
    ))
    fig.add_trace(go.Scatter(
        x=history_df["tick"].tolist(),
        y=history_df["queued_vehicles"].tolist(),
        mode="lines",
        name="Queued",
        line=dict(color=THEME_COLORS["alert_coral"], width=2.0, dash="dot")
    ))
    fig.add_trace(go.Scatter(
        x=history_df["tick"].tolist(),
        y=history_df["completed_vehicles"].tolist(),
        mode="lines",
        name="Completed",
        line=dict(color=THEME_COLORS["accent_primary"], width=2.3)
    ))
    _apply_soft_layout(fig, "Fleet Status Over Time", height=290)
    fig.update_xaxes(title_text="Simulation Tick")
    if x_max is not None:
        cur_max_x = float(history_df["tick"].max()) if not history_df.empty else 0.0
        fig.update_xaxes(range=[0, max(10.0, float(x_max), cur_max_x)])
    fig.update_yaxes(title_text="Vehicles")
    if y_max is not None:
        fig.update_yaxes(range=[0, max(5.0, round(float(y_max) * 1.08, 1))])
    return fig


def render_speed_density_trend(history_df: pd.DataFrame) -> go.Figure:
    """Renders dual-axis plot of Network Density vs Average Speed."""
    if history_df.empty:
        return _empty_soft_figure("Advance simulation to view speed & density.", "Density vs Speed")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=history_df["tick"],
            y=history_df["average_density"] * 100.0,
            name="Density (%)",
            line=dict(color=THEME_COLORS["alert_coral"], width=2.2)
        ),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(
            x=history_df["tick"],
            y=history_df["average_speed_kmh"],
            name="Speed (km/h)",
            line=dict(color=THEME_COLORS["primary_dark"], width=2.2, dash="dash")
        ),
        secondary_y=True
    )
    _apply_soft_layout(fig, "Traffic Density & Speed Trend", height=290)
    fig.update_yaxes(title_text="Density (%)", secondary_y=False, gridcolor=GRID_COLOR)
    fig.update_yaxes(title_text="Speed (km/h)", secondary_y=True, gridcolor=GRID_COLOR)
    return fig


def render_strategy_comparison_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Renders grouped bar chart comparing Travel Time, Delay, and Queue across strategies."""
    if comparison_df.empty:
        return _empty_soft_figure("Run benchmark to view strategy comparison.", "Strategy Comparison")

    strategies = comparison_df["Strategy"].tolist()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=strategies,
        y=comparison_df["Avg Travel Time (s)"].tolist(),
        name="Completed Avg Time (s)",
        marker_color=THEME_COLORS["idle_road"]
    ))
    fig.add_trace(go.Bar(
        x=strategies,
        y=comparison_df["Avg Delay (s)"].tolist(),
        name="Avg Delay (s)",
        marker_color=THEME_COLORS["moderate_orange"]
    ))
    fig.add_trace(go.Bar(
        x=strategies,
        y=comparison_df["Avg Queue (veh)"].tolist(),
        name="Avg Queue (veh)",
        marker_color=THEME_COLORS["alert_coral"]
    ))
    _apply_soft_layout(fig, "Mobility Metrics by Strategy", height=320)
    fig.update_layout(barmode="group")
    return fig


def render_radar_comparison(metrics_by_strategy: Dict[str, PerformanceMetrics]) -> go.Figure:
    """Renders normalized multi-criteria radar chart in the Mint Mist palette."""
    fig = go.Figure()
    if not metrics_by_strategy:
        return _empty_soft_figure("No comparison data.", "Multi-Criteria Radar")

    categories = ["Throughput %", "Speed", "Time Efficiency", "Delay Control", "Queue Control"]
    max_tt = max(max(m.average_travel_time for m in metrics_by_strategy.values()), 1.0)
    max_delay = max(max(m.average_delay for m in metrics_by_strategy.values()), 1.0)
    max_queue = max(max(m.average_queue_length for m in metrics_by_strategy.values()), 1.0)

    color_map = {
        "Independent": THEME_COLORS["idle_road"],
        "Route Advisories": THEME_COLORS["accent_soft"],
        "Congestion Pricing": THEME_COLORS["moderate_orange"],
        "Dynamic Lanes": THEME_COLORS["accent_muted"],
        "Combined": THEME_COLORS["accent_primary"]
    }

    for strat, m in metrics_by_strategy.items():
        values = [
            m.completion_rate_pct,
            min(100.0, (m.average_speed_kmh / 50.0) * 100.0),
            max(0.0, 100.0 - (m.average_travel_time / max_tt) * 100.0),
            max(0.0, 100.0 - (m.average_delay / max_delay) * 100.0),
            max(0.0, 100.0 - (m.average_queue_length / max_queue) * 100.0)
        ]
        values.append(values[0])
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill="toself",
            name=strat,
            line=dict(color=color_map.get(strat, THEME_COLORS["accent_primary"]), width=2),
            opacity=0.55
        ))

    fig.update_layout(
        template="plotly_white",
        title=dict(text="Normalized Performance Profile", font=dict(size=14, color=TEXT_PRIMARY, family=FONT_FAMILY)),
        height=320,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID_COLOR),
            bgcolor=BG_SURFACE
        ),
        paper_bgcolor=BG_SURFACE,
        font=dict(color=TEXT_PRIMARY, size=11, family=FONT_FAMILY),
        margin=dict(l=36, r=36, t=44, b=36)
    )
    return fig


def render_density_chart(history_df: pd.DataFrame, x_max: Optional[int] = None) -> go.Figure:
    """Renders network traffic density (%) over simulation ticks."""
    if history_df.empty:
        return _empty_soft_figure("No telemetry recorded yet.", "Traffic Density (%)", height=240)
    densities = (history_df["average_density"] * 100.0).tolist()
    fig = go.Figure(go.Scatter(
        x=history_df["tick"].tolist(),
        y=densities,
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(229, 72, 77, 0.14)",
        line=dict(color=THEME_COLORS["alert_coral"], width=2.2),
        name="Density (%)"
    ))
    _apply_soft_layout(fig, "Traffic Density (%)", height=240)
    fig.update_xaxes(title_text="Tick")
    if x_max is not None:
        fig.update_xaxes(range=[0, max(10.0, float(x_max), float(history_df["tick"].max()))])
    peak_d = max(densities) if densities else 0.0
    fig.update_yaxes(title_text="%", range=[0, max(20.0, math.ceil((peak_d + 2.0) / 10.0) * 10.0)])
    return fig


def render_speed_chart(history_df: pd.DataFrame, x_max: Optional[int] = None) -> go.Figure:
    """Renders average network speed (km/h) over simulation ticks."""
    if history_df.empty:
        return _empty_soft_figure("No telemetry recorded yet.", "Average Speed (km/h)", height=240)
    speeds = history_df["average_speed_kmh"].tolist()
    fig = go.Figure(go.Scatter(
        x=history_df["tick"].tolist(),
        y=speeds,
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(52, 165, 138, 0.15)",
        line=dict(color=THEME_COLORS["accent_primary"], width=2.2),
        name="Speed (km/h)"
    ))
    _apply_soft_layout(fig, "Average Speed (km/h)", height=240)
    fig.update_xaxes(title_text="Tick")
    if x_max is not None:
        fig.update_xaxes(range=[0, max(10.0, float(x_max), float(history_df["tick"].max()))])
    peak_s = max(speeds) if speeds else 0.0
    fig.update_yaxes(title_text="km/h", range=[0, max(90.0, math.ceil((peak_s + 5.0) / 10.0) * 10.0)])
    return fig


def render_completion_chart(
    history_df: pd.DataFrame,
    x_max: Optional[int] = None,
    y_max: Optional[float] = None,
) -> go.Figure:
    """Renders completed vs active vehicle counts over simulation ticks."""
    if history_df.empty:
        return _empty_soft_figure("No telemetry recorded yet.", "Vehicle Completion", height=240)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history_df["tick"].tolist(),
        y=history_df["completed_vehicles"].tolist(),
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(52, 165, 138, 0.16)",
        line=dict(color=THEME_COLORS["accent_primary"], width=2.2),
        name="Completed"
    ))
    fig.add_trace(go.Scatter(
        x=history_df["tick"].tolist(),
        y=history_df["active_vehicles"].tolist(),
        mode="lines",
        line=dict(color=THEME_COLORS["primary_dark"], width=2.0, dash="dot"),
        name="Active"
    ))
    _apply_soft_layout(fig, "Vehicle Completion", height=240)
    fig.update_xaxes(title_text="Tick")
    if x_max is not None:
        fig.update_xaxes(range=[0, max(10.0, float(x_max), float(history_df["tick"].max()))])
    fig.update_yaxes(title_text="Vehicles")
    if y_max is not None:
        fig.update_yaxes(range=[0, max(5.0, round(float(y_max) * 1.08, 1))])
    return fig


def render_travel_time_comparison_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Compares Completed-Only vs All-Departed Average Travel Time across strategies."""
    if comparison_df.empty:
        return _empty_soft_figure("Run benchmark to view travel-time comparison.", "Travel-Time Comparison")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=comparison_df["Strategy"],
        y=comparison_df["Avg Travel Time (s)"],
        name="Completed-Only Avg (s)",
        marker_color=THEME_COLORS["idle_road"]
    ))
    if "All-Departed Avg (s)" in comparison_df.columns:
        fig.add_trace(go.Bar(
            x=comparison_df["Strategy"],
            y=comparison_df["All-Departed Avg (s)"],
            name="All-Departed Avg (s)",
            marker_color=THEME_COLORS["accent_primary"]
        ))
    _apply_soft_layout(fig, "Travel-Time Comparison (Completed vs All-Departed)", height=310)
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Seconds")
    return fig


def render_congestion_comparison_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Compares Average Density (%) and Average Queue Length across strategies."""
    if comparison_df.empty:
        return _empty_soft_figure("Run benchmark to view congestion comparison.", "Congestion Comparison")
    densities = [float(str(x).replace("%", "")) for x in comparison_df["Avg Density"]]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=comparison_df["Strategy"],
            y=densities,
            name="Avg Density (%)",
            marker_color=THEME_COLORS["moderate_orange"]
        ),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(
            x=comparison_df["Strategy"],
            y=comparison_df["Avg Queue (veh)"],
            name="Avg Queue (veh)",
            mode="lines+markers",
            line=dict(color=THEME_COLORS["alert_coral"], width=2.3),
            marker=dict(size=7)
        ),
        secondary_y=True
    )
    _apply_soft_layout(fig, "Congestion & Queue Comparison", height=310)
    fig.update_yaxes(title_text="Avg Density (%)", secondary_y=False, gridcolor=GRID_COLOR)
    fig.update_yaxes(title_text="Avg Queue (veh)", secondary_y=True, gridcolor=GRID_COLOR)
    return fig


def render_throughput_comparison_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Compares Completion Rate (%) across strategies."""
    if comparison_df.empty:
        return _empty_soft_figure("Run benchmark to view throughput comparison.", "Throughput Comparison")
    comp_pct = [float(str(x).replace("%", "")) for x in comparison_df["Completion %"]]
    colors = [
        THEME_COLORS["idle_road"],
        THEME_COLORS["accent_soft"],
        THEME_COLORS["accent_muted"],
        THEME_COLORS["accent_primary"],
        THEME_COLORS["primary_dark"]
    ]
    fig = go.Figure(go.Bar(
        x=comparison_df["Strategy"],
        y=comp_pct,
        text=[f"{v:.1f}%" for v in comp_pct],
        textposition="outside",
        marker_color=colors[:len(comp_pct)]
    ))
    _apply_soft_layout(fig, "Throughput (Completion Rate %)", height=310)
    fig.update_yaxes(title_text="Completion %", range=[0, 115])
    return fig


def render_architecture_diagram() -> go.Figure:
    """Renders a clean Mint Mist system architecture diagram."""
    fig = go.Figure()
    boxes = [
        (1.0, 3.0, "Road Network<br>(NetworkX Graph)", THEME_COLORS["card_bg"], THEME_COLORS["border"]),
        (3.0, 3.0, "Vehicle Agents<br>(Autonomous Fleet)", THEME_COLORS["card_bg"], THEME_COLORS["accent_muted"]),
        (5.0, 3.0, "Route Planner<br>(Dijkstra & A*)", THEME_COLORS["card_bg"], THEME_COLORS["border"]),
        (3.0, 1.8, "Discrete-Time Simulation Engine", THEME_COLORS["light_surface"], THEME_COLORS["accent_primary"]),
        (1.5, 0.6, "Traffic Monitor<br>(Density & Queues)", THEME_COLORS["secondary_bg"], THEME_COLORS["accent_muted"]),
        (4.5, 0.6, "AI Coordinator<br>(Advisories · Pricing · Lanes)", THEME_COLORS["light_surface"], THEME_COLORS["accent_primary"]),
        (3.0, -0.5, "Performance Evaluation & Analytics UI", THEME_COLORS["background"], THEME_COLORS["border"]),
    ]
    edges = [
        (1.0, 2.65, 2.4, 2.05),
        (3.0, 2.65, 3.0, 2.05),
        (5.0, 2.65, 3.6, 2.05),
        (2.4, 1.55, 1.6, 0.95),
        (2.2, 0.6, 3.8, 0.6),
        (4.4, 0.95, 3.6, 1.55),
        (3.0, 1.55, 3.0, -0.15),
    ]
    for x0, y0, x1, y1 in edges:
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.6, arrowcolor=THEME_COLORS["text_secondary"]
        )
    for x, y, text, bg, border_col in boxes:
        fig.add_shape(
            type="rect", x0=x-0.8, y0=y-0.32, x1=x+0.8, y1=y+0.32,
            fillcolor=bg, line=dict(color=border_col, width=1.6)
        )
        fig.add_annotation(
            x=x, y=y, text=text, showarrow=False,
            font=dict(color=TEXT_PRIMARY, size=11, family=FONT_FAMILY)
        )
    fig.update_layout(
        template="plotly_white",
        height=360,
        plot_bgcolor=BG_SURFACE,
        paper_bgcolor=BG_SURFACE,
        xaxis=dict(range=[0, 6], visible=False),
        yaxis=dict(range=[-1.0, 3.6], visible=False),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    return fig
