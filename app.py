"""
Smart City Traffic Intelligence — Minimalist Soft UI (Second Design Pass).
Group 17 — Artificial Intelligence Foundations.
"""
from __future__ import annotations
from typing import Optional
import time
import pandas as pd
import streamlit as st

from simulation.engine import SimulationEngine, SimulationState
from evaluation.comparison import StrategyComparator, BenchmarkResult, MultiSeedBenchmarkResult
from visualization.city_map import render_city_network_map, render_live_city_map
from visualization.charts import (
    render_live_telemetry_chart,
    render_metrics_timeline,
    render_strategy_comparison_chart,
    render_density_chart,
    render_speed_chart,
    render_completion_chart,
    render_travel_time_comparison_chart,
    render_congestion_comparison_chart,
    render_throughput_comparison_chart,
    render_architecture_diagram
)
from config import (
    SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN,
    THEME_COLORS
)
from theme_3d import inject_3d_theme


# ---------------------------------------------------------
# Page Configuration & Soft 3D Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="Smart City — Traffic Intelligence",
    page_icon="▪",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_3d_theme()

PLOTLY_CONFIG = {"displayModeBar": False}
SIM_REFRESH_SECONDS = 0.9
TELEMETRY_REFRESH_SECONDS = 2.0


# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
def get_engine() -> SimulationEngine:
    if "engine" not in st.session_state:
        eng = SimulationEngine()
        eng.setup(
            scenario_name=SCENARIO_NORMAL,
            vehicle_count=40,
            strategy_name="Independent",
            seed=42,
            network_type="smart_city",
            arrival_interval=1
        )
        st.session_state.engine = eng
    return st.session_state.engine


engine = get_engine()

for key, default in [
    ("current_page", "Overview"),
    ("benchmark_result", None),
    ("multi_seed_result", None),
    ("sim_delay", 0.15),
    ("confirm_sidebar_reset", False),
    ("confirm_live_reset", False)
]:
    if key not in st.session_state:
        st.session_state[key] = default


def state_pill_html(state: SimulationState, extra_text: str = "") -> str:
    """Colour-coded status pill matching Mint Mist tokens."""
    styles = {
        SimulationState.RUNNING: (THEME_COLORS["light_surface"], "#A9D5C6", THEME_COLORS["primary_dark"], THEME_COLORS["accent_primary"]),
        SimulationState.PAUSED: ("#FCEBEC", "#F2B6B8", THEME_COLORS["primary_dark"], THEME_COLORS["alert_coral"]),
        SimulationState.READY: (THEME_COLORS["secondary_bg"], THEME_COLORS["border"], THEME_COLORS["primary_dark"], THEME_COLORS["accent_muted"]),
        SimulationState.COMPLETED: (THEME_COLORS["light_surface"], "#A9D5C6", THEME_COLORS["primary_dark"], THEME_COLORS["accent_primary"]),
        SimulationState.IDLE: (THEME_COLORS["secondary_bg"], THEME_COLORS["border"], THEME_COLORS["text_secondary"], THEME_COLORS["idle_road"]),
    }
    bg, border, fg, dot = styles.get(state, (THEME_COLORS["secondary_bg"], THEME_COLORS["border"], THEME_COLORS["text_secondary"], THEME_COLORS["idle_road"]))
    label = f"{state.value}" + (f" · {extra_text}" if extra_text else "")
    return (
        f"<span class='status-pill' style='background:{bg}; border-color:{border}; color:{fg};'>"
        f"<span class='status-dot' style='background:{dot};'></span>{label}</span>"
    )


def render_header(title: str, subtitle: str, chip_text: str = "", state: Optional[SimulationState] = None) -> None:
    c_left, c_right = st.columns([7, 5])
    with c_left:
        st.markdown(f"<div class='page-title'>{title}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='page-subtitle'>{subtitle}</div>", unsafe_allow_html=True)
    with c_right:
        if state is not None:
            st.markdown(
                f"<div style='text-align:right; padding-top:4px;'>{state_pill_html(state, chip_text)}</div>",
                unsafe_allow_html=True
            )
        elif chip_text:
            st.markdown(
                f"<div style='text-align:right; padding-top:4px;'>"
                f"<span class='status-pill' style='background:{THEME_COLORS['light_surface']}; border-color:{THEME_COLORS['border']}; color:{THEME_COLORS['primary_dark']};'>{chip_text}</span></div>",
                unsafe_allow_html=True
            )


def get_traffic_status(avg_density: float, total_vehicles_on_road: int) -> tuple[str, str]:
    if total_vehicles_on_road == 0:
        return "Idle", THEME_COLORS["idle_road"]
    if avg_density < 0.40:
        return "Low", THEME_COLORS["low_congestion"]
    elif avg_density < 0.70:
        return "Moderate", THEME_COLORS["moderate_congestion"]
    elif avg_density < 0.90:
        return "High", THEME_COLORS["high_congestion"]
    return "Severe", THEME_COLORS["severe_congestion"]


def get_road_distribution(eng: SimulationEngine) -> dict:
    counts = {"IDLE": 0, "LOW": 0, "MODERATE": 0, "HIGH": 0, "SEVERE": 0}
    for road in eng.network.roads.values():
        if road.vehicle_count == 0:
            counts["IDLE"] += 1
        else:
            counts[road.congestion_level] += 1
    return counts


def generate_traffic_insight(eng: SimulationEngine) -> str:
    """One-line dynamic insight derived from actual simulation telemetry."""
    net = eng.network.get_network_summary()
    fleet = eng.fleet_manager.get_fleet_summary()
    roads = list(eng.network.roads.values())

    if eng.tick == 0:
        return (
            f"<b>Simulation ready</b> — all {net['num_roads']} road segments are idle; "
            f"{fleet['total_vehicles']} vehicles staged for {eng.scenario_name} ({eng.strategy_name})."
        )

    active_roads = [r for r in roads if r.vehicle_count > 0]
    busiest = max(roads, key=lambda r: (r.density, r.queue_length)) if roads else None
    hist = eng.monitor.history
    avg_speed = hist[-1].average_speed_kmh if hist else 0.0

    if not active_roads:
        return (
            f"<b>Network clear</b> — {fleet['completed_vehicles']}/{fleet['total_vehicles']} journeys completed "
            f"at Tick {eng.tick} (mean speed {avg_speed:.1f} km/h)."
        )

    if busiest and busiest.density >= 0.70:
        lead = f"<b>Congestion rising on {busiest.end_node}</b> ({busiest.road_id} at {busiest.density*100:.0f}% occupancy"
        if net["total_queued"] > 0:
            lead += f", {net['total_queued']} queued)"
        else:
            lead += ")"
    elif busiest and busiest.density >= 0.40:
        lead = f"<b>Moderate traffic building</b> — busiest link {busiest.road_id} ({busiest.start_node} &rarr; {busiest.end_node}) at {busiest.density*100:.0f}% occupancy"
    else:
        lead = f"<b>Network flowing normally</b> — {len(active_roads)} active segments at {avg_speed:.1f} km/h average speed"

    if eng.strategy_name != "Independent":
        adv_acc = sum(1 for e in eng.coordinator.advisory_system.events if e.accepted)
        lane_shifts = len(eng.coordinator.lane_system.events)
        tolls_active = sum(1 for r in roads if r.toll > 0)
        return f"{lead}. Coordination active: {adv_acc} reroute(s), {tolls_active} tolled link(s), {lane_shifts} lane shift(s)."
    return f"{lead}. {fleet['completed_vehicles']}/{fleet['total_vehicles']} journeys completed."


def render_kpi_grid(eng: SimulationEngine) -> None:
    """Renders 4 + 2 uniform Mint Mist st.metric cards with congestion-only alert color."""
    fleet = eng.fleet_manager.get_fleet_summary()
    net = eng.network.get_network_summary()
    cong_lbl, cong_col = get_traffic_status(net["average_density"], net["total_vehicles"])

    # Highlight congestion metric value only when elevated (restrained coral -> severe red)
    val_col_map = {
        "Moderate": "#C95256",
        "High": THEME_COLORS["alert_coral"],
        "Severe": THEME_COLORS["severe_red"],
    }
    cong_val_css = f"color: {val_col_map[cong_lbl]};" if cong_lbl in val_col_map else ""
    st.markdown(
        f"<style>"
        f"div[data-testid='stColumn']:has(.cong-marker) div[data-testid='stMetric']::before,"
        f"div[data-testid='column']:has(.cong-marker) div[data-testid='stMetric']::before {{ background: {cong_col}; }}"
        f"div[data-testid='stColumn']:has(.cong-marker) div[data-testid='stMetricValue'],"
        f"div[data-testid='column']:has(.cong-marker) div[data-testid='stMetricValue'] {{ {cong_val_css} }}"
        f"</style>",
        unsafe_allow_html=True
    )

    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
    with r1_c1:
        st.metric("Total vehicles", f"{fleet['total_vehicles']}", f"{eng.scenario_name}", delta_color="off")
    with r1_c2:
        st.metric("Active vehicles", f"{fleet['active_vehicles']}", f"{fleet['waiting_vehicles']} queued", delta_color="off")
    with r1_c3:
        st.metric("Completed journeys", f"{fleet['completed_vehicles']}", f"{fleet['completion_rate']:.0f}% done", delta_color="off")
    with r1_c4:
        st.metric("Average travel time", f"{fleet['average_travel_time']:.1f} s", f"+{fleet['average_delay']:.1f} s delay", delta_color="off")

    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        st.markdown("<span class='cong-marker' style='display:none;'></span>", unsafe_allow_html=True)
        delta_mode = "inverse" if cong_lbl in ("High", "Severe") else "off"
        st.metric(
            "Network congestion",
            f"{net['average_density']*100:.1f}%",
            f"{cong_lbl} · {net['total_vehicles']}/{net['total_capacity']} slots",
            delta_color=delta_mode
        )
    with r2_c2:
        st.metric("Active strategy", f"{eng.strategy_name}", f"Seed {eng.seed} · {eng.network.name}", delta_color="off")


def render_health_card(eng: SimulationEngine) -> None:
    """Traffic Health Summary card matching map height."""
    net = eng.network.get_network_summary()
    dist = get_road_distribution(eng)
    total_r = max(1, net["num_roads"])

    bar_segments = "".join(
        f"<div style='width:{(dist[k]/total_r)*100:.2f}%; background:{col};'></div>"
        for k, col in [
            ("IDLE", THEME_COLORS["idle_road"]),
            ("LOW", THEME_COLORS["low_congestion"]),
            ("MODERATE", THEME_COLORS["moderate_congestion"]),
            ("HIGH", THEME_COLORS["high_congestion"]),
            ("SEVERE", THEME_COLORS["severe_congestion"]),
        ] if dist[k] > 0
    )

    rows_html = "".join(
        f"<div class='health-row'>"
        f"<span><span class='status-dot' style='background:{col}; margin-right:8px;'></span>{lbl}</span>"
        f"<b style='color:{THEME_COLORS['text_primary']};'>{dist[k]}</b>"
        f"</div>"
        for k, lbl, col in [
            ("IDLE", "Idle (0 vehicles)", THEME_COLORS["idle_road"]),
            ("LOW", "Low (<40%)", THEME_COLORS["low_congestion"]),
            ("MODERATE", "Moderate (40–70%)", THEME_COLORS["moderate_congestion"]),
            ("HIGH", "High (70–90%)", THEME_COLORS["high_congestion"]),
            ("SEVERE", "Severe (90%+)", THEME_COLORS["severe_congestion"]),
        ]
    )

    st.markdown(
        f"<div class='ui-card' style='min-height: 390px; display:flex; flex-direction:column; justify-content:space-between;'>"
        f"<div>"
        f"<div style='font-size:12.5px; font-weight:700; color:{THEME_COLORS['text_secondary']}; text-transform:uppercase; letter-spacing:.05em;'>"
        f"Road Congestion ({total_r} segments)</div>"
        f"<div class='dist-bar'>{bar_segments}</div>"
        f"{rows_html}"
        f"</div>"
        f"<div>"
        f"<div class='health-stat-chip'><span style='color:{THEME_COLORS['text_secondary']};'>Network occupancy</span><b style='color:{THEME_COLORS['accent_primary']};'>{net['total_vehicles']} / {net['total_capacity']}</b></div>"
        f"<div class='health-stat-chip'><span style='color:{THEME_COLORS['text_secondary']};'>Intersection queues</span><b style='color:{THEME_COLORS['severe_congestion'] if net['total_queued'] > 0 else THEME_COLORS['text_primary']};'>{net['total_queued']} vehicles</b></div>"
        f"<div class='health-stat-chip'><span style='color:{THEME_COLORS['text_secondary']};'>Simulation clock</span><b style='color:{THEME_COLORS['text_primary']};'>{eng.tick * eng.delta_t:.0f} s</b></div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True
    )


def render_top_control_bar(eng: SimulationEngine, key_prefix: str, include_step: bool = True) -> None:
    """Compact control bar with Start, Pause/Resume, Step, Reset, Progress bar, and Status pill."""
    cols = st.columns([1.2, 1.2, 1.1, 1.2, 3.3, 2.0]) if include_step else st.columns([1.3, 1.3, 1.3, 4.0, 2.1])

    with cols[0]:
        if st.button("Start", key=f"{key_prefix}_start", type="primary", use_container_width=True,
                     disabled=(eng.state != SimulationState.READY),
                     help="Start autonomous simulation playback."):
            eng.start()
            st.session_state["_skip_frag_step"] = True
            st.toast("Simulation started.", icon="▶️")
            st.rerun()

    with cols[1]:
        if eng.state == SimulationState.PAUSED:
            if st.button("Resume", key=f"{key_prefix}_resume", use_container_width=True,
                         help="Resume paused simulation."):
                eng.resume()
                st.session_state["_skip_frag_step"] = True
                st.toast("Simulation resumed.", icon="⏯️")
                st.rerun()
        else:
            if st.button("Pause", key=f"{key_prefix}_pause", use_container_width=True,
                         disabled=(eng.state != SimulationState.RUNNING),
                         help="Pause running simulation."):
                eng.pause()
                st.toast("Simulation paused.", icon="⏸️")
                st.rerun()

    idx_offset = 0
    if include_step:
        idx_offset = 1
        with cols[2]:
            if st.button("Step", key=f"{key_prefix}_step", use_container_width=True,
                         disabled=(eng.state == SimulationState.COMPLETED),
                         help="Advance the simulation by 1 tick."):
                eng.step()
                st.rerun()

    with cols[2 + idx_offset]:
        if st.button("Reset", key=f"{key_prefix}_reset", use_container_width=True,
                     help="Reset vehicles, queues, and clock back to Tick 0."):
            eng.reset()
            st.toast("Simulation reset to Tick 0.", icon="🔄")
            st.rerun()

    progress_frac = min(1.0, eng.tick / max(1, eng.max_ticks))
    with cols[3 + idx_offset]:
        st.progress(progress_frac, text=f"Tick {eng.tick}/{eng.max_ticks} ({progress_frac*100:.0f}%)")

    with cols[4 + idx_offset]:
        st.markdown(
            f"<div style='text-align:right; padding-top:4px;'>{state_pill_html(eng.state)}</div>",
            unsafe_allow_html=True
        )


# ---------------------------------------------------------
# Sidebar Icon-Based Navigation & Compact Configuration
# ---------------------------------------------------------
NAV_ITEMS = [
    ("Overview", "◫"),
    ("Live Simulation", "◉"),
    ("Vehicles", "▤"),
    ("Coordination", "⇄"),
    ("Analytics", "◩"),
    ("About", "ⓘ"),
]

with st.sidebar:
    st.markdown(
        f"<div style='padding-bottom: 10px; border-bottom: 1px solid rgba(38,53,46,0.09); margin-bottom: 10px;'>"
        f"<div style='font-size:16.5px; font-weight:700; color:{THEME_COLORS['text_primary']};'>Smart City</div>"
        f"<div style='font-size:12px; color:{THEME_COLORS['accent_primary']}; font-weight:600;'>Traffic Intelligence</div>"
        f"</div>",
        unsafe_allow_html=True
    )

    st.markdown("<div class='nav-block'>", unsafe_allow_html=True)
    for nav_name, nav_icon in NAV_ITEMS:
        is_active = (st.session_state.current_page == nav_name)
        if st.button(
            f"{nav_icon}  {nav_name}",
            key=f"nav_{nav_name}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
            help=f"Open {nav_name} view"
        ):
            st.session_state.current_page = nav_name
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    page = st.session_state.current_page

    st.markdown("<div style='border-top: 1px solid rgba(38,53,46,0.09); margin: 10px 0;'></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:11.5px; font-weight:700; color:{THEME_COLORS['text_secondary']}; letter-spacing:.05em; margin-bottom:6px;'>SIMULATION SETUP</div>", unsafe_allow_html=True)

    network_choice = st.selectbox(
        "Network Topology",
        ["Metro Smart City (12 Nodes)", "Commuter Arterial (6 Nodes)"],
        index=0 if engine.network_type == "smart_city" else 1,
        help="Choose between the 12-node city grid with bypasses or the 6-node arterial corridor."
    )
    net_key = "smart_city" if "Metro" in network_choice else "arterial"

    scenario_list = [SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN]
    scenario_choice = st.selectbox(
        "Traffic Scenario",
        scenario_list,
        index=scenario_list.index(engine.scenario_name),
        help="Sets vehicle demand distribution and arrival burst patterns."
    )

    strategy_list = ["Independent", "Route Advisories", "Congestion Pricing", "Dynamic Lanes", "Combined"]
    strategy_choice = st.selectbox(
        "Coordination Strategy",
        strategy_list,
        index=strategy_list.index(engine.strategy_name),
        help="Select baseline uncoordinated routing or an AI coordination mechanism."
    )

    with st.expander("Advanced Settings", expanded=False):
        veh_count = st.slider(
            "Number of Vehicles", 10, 100, engine.vehicle_count, 5,
            help="Total number of autonomous vehicle agents generated for the scenario."
        )
        sim_duration_ticks = st.slider(
            "Duration (Ticks)", 60, 300, engine.max_ticks, 20,
            help="Maximum simulation horizon (1 tick = 3 simulated seconds)."
        )
        arrival_interval = st.slider(
            "Arrival Interval (Ticks)", 1, 5, engine.arrival_interval, 1,
            help="Tick spacing between staggered vehicle departure waves."
        )
        random_seed = st.number_input(
            "Random Seed", min_value=1, max_value=9999, value=engine.seed, step=1,
            help="Reproducible seed controlling vehicle origins, destinations, and profiles."
        )

    if st.button("Apply & Reset", use_container_width=True, type="primary",
                 help="Apply topology, scenario, and strategy changes and reset simulation to Tick 0."):
        engine.max_ticks = sim_duration_ticks
        engine.setup(
            scenario_name=scenario_choice,
            vehicle_count=veh_count,
            strategy_name=strategy_choice,
            seed=int(random_seed),
            network_type=net_key,
            arrival_interval=arrival_interval
        )
        st.session_state.benchmark_result = None
        st.session_state.multi_seed_result = None
        st.toast("Configuration applied. Simulation reset to Tick 0.", icon="🔄")
        st.rerun()

    st.markdown(
        f"<div style='margin-top:10px; padding-top:8px; border-top:1px solid {THEME_COLORS['border']}; font-size:12px; color:{THEME_COLORS['text_secondary']};'>"
        f"State: <b style='color:{THEME_COLORS['text_primary']};'>{engine.state.value}</b> · Tick <b>{engine.tick}/{engine.max_ticks}</b>"
        f"</div>",
        unsafe_allow_html=True
    )


# =========================================================
# PAGE 1: OVERVIEW
# =========================================================
if page == "Overview":
    render_header(
        "Traffic Intelligence Overview",
        "Urban road network health, KPI summary, and multi-agent coordination status.",
        chip_text=f"{engine.scenario_name}",
        state=engine.state
    )

    @st.fragment(run_every=SIM_REFRESH_SECONDS if engine.state == SimulationState.RUNNING else None)
    def _overview_live_fragment():
        if engine.state == SimulationState.RUNNING:
            if st.session_state.pop("_skip_frag_step", False):
                pass
            else:
                engine.step()
                if engine.state == SimulationState.COMPLETED:
                    st.toast("Simulation completed.", icon="✅")
                    st.rerun()

        render_top_control_bar(engine, key_prefix="ov", include_step=False)
        render_kpi_grid(engine)
        has_severe = any(r.vehicle_count > 0 and r.density >= 0.90 for r in engine.network.roads.values())
        insight_cls = "insight-line alert" if has_severe else "insight-line"
        st.markdown(f"<div class='{insight_cls}'>{generate_traffic_insight(engine)}</div>", unsafe_allow_html=True)

        col_map, col_health = st.columns([8, 4])
        with col_map:
            st.markdown("<div class='section-heading'>Network Snapshot</div>", unsafe_allow_html=True)
            render_live_city_map(
                engine.network, engine.fleet_manager,
                tick=engine.tick, show_road_labels=False, height=390, key="ov_live_map"
            )

        with col_health:
            st.markdown("<div class='section-heading'>Traffic Health Summary</div>", unsafe_allow_html=True)
            render_health_card(engine)

    _overview_live_fragment()

    @st.fragment(run_every=TELEMETRY_REFRESH_SECONDS if engine.state == SimulationState.RUNNING else None)
    def _overview_telemetry_fragment():
        st.markdown("<div class='section-heading'>Telemetry Trends</div>", unsafe_allow_html=True)
        hist_df = engine.monitor.history_to_dataframe()
        t_c1, t_c2, t_c3 = st.columns(3)
        with t_c1:
            render_live_telemetry_chart(
                render_density_chart(hist_df, x_max=engine.max_ticks),
                height=240,
                key="ov_density",
            )
        with t_c2:
            render_live_telemetry_chart(
                render_speed_chart(hist_df, x_max=engine.max_ticks),
                height=240,
                key="ov_speed",
            )
        with t_c3:
            render_live_telemetry_chart(
                render_completion_chart(hist_df, x_max=engine.max_ticks, y_max=engine.vehicle_count),
                height=240,
                key="ov_completion",
            )

    _overview_telemetry_fragment()


# =========================================================
# PAGE 2: LIVE SIMULATION
# =========================================================
elif page == "Live Simulation":
    render_header(
        "Live Simulation",
        "Interactive playback workspace for real-time vehicle trajectories and congestion.",
        chip_text=f"{engine.strategy_name}",
        state=engine.state
    )

    @st.fragment(run_every=SIM_REFRESH_SECONDS if engine.state == SimulationState.RUNNING else None)
    def _live_sim_fragment():
        if engine.state == SimulationState.RUNNING:
            if st.session_state.pop("_skip_frag_step", False):
                pass
            else:
                engine.step()
                if engine.state == SimulationState.COMPLETED:
                    st.toast("Simulation completed.", icon="✅")
                    st.rerun()

        render_top_control_bar(engine, key_prefix="live", include_step=True)

        opt_col1, opt_col2, _ = st.columns([2, 2, 8])
        show_labels = opt_col1.checkbox("Show road loads", value=True, key="live_show_labels", help="Display active vehicle/capacity labels on occupied roads.")
        if opt_col2.button("Advance +10 Ticks", key="live_adv10", use_container_width=True, disabled=(engine.state == SimulationState.COMPLETED),
                           help="Quickly advance 10 simulation ticks."):
            for _ in range(10):
                if engine.state == SimulationState.COMPLETED:
                    break
                engine.step()
            st.rerun()

        has_severe_live = any(r.vehicle_count > 0 and r.density >= 0.90 for r in engine.network.roads.values())
        live_insight_cls = "insight-line alert" if has_severe_live else "insight-line"
        st.markdown(f"<div class='{live_insight_cls}'>{generate_traffic_insight(engine)}</div>", unsafe_allow_html=True)
        render_live_city_map(
            engine.network, engine.fleet_manager,
            tick=engine.tick, show_road_labels=show_labels, height=560, key="live_sim_map"
        )

    _live_sim_fragment()

    @st.fragment(run_every=TELEMETRY_REFRESH_SECONDS if engine.state == SimulationState.RUNNING else None)
    def _live_telemetry_fragment():
        with st.expander("Road Segment Telemetry & Timeline", expanded=False):
            t1, t2 = st.columns(2)
            with t1:
                df_roads = engine.monitor.roads_to_dataframe()
                if not df_roads.empty:
                    st.dataframe(df_roads, width="stretch", height=290, hide_index=True, key="live_roads_table")
            with t2:
                hist_df = engine.monitor.history_to_dataframe()
                render_live_telemetry_chart(
                    render_metrics_timeline(hist_df, x_max=engine.max_ticks, y_max=engine.vehicle_count),
                    height=290,
                    key="live_timeline",
                )

    _live_telemetry_fragment()


# =========================================================
# PAGE 3: VEHICLES
# =========================================================
elif page == "Vehicles":
    render_header(
        "Vehicle Management",
        "Search and filter individual vehicle agents, inspect paths, or add a custom trip.",
        f"{len(engine.fleet_manager.vehicles)} Vehicles"
    )

    df_fleet = engine.fleet_manager.to_dataframe()
    if not df_fleet.empty:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            search_id = st.text_input("Search Vehicle ID", placeholder="e.g. VEH_001")
        with f2:
            status_opts = ["PENDING", "EN_ROUTE", "WAITING", "COMPLETED"]
            status_filter = st.multiselect("Status", status_opts, default=status_opts)
        with f3:
            origins = ["All"] + sorted(df_fleet["origin"].unique().tolist())
            origin_filter = st.selectbox("Origin", origins)
        with f4:
            dests = ["All"] + sorted(df_fleet["destination"].unique().tolist())
            dest_filter = st.selectbox("Destination", dests)

        filtered = df_fleet[df_fleet["status"].isin(status_filter)]
        if search_id.strip():
            filtered = filtered[filtered["vehicle_id"].str.contains(search_id.strip(), case=False, na=False)]
        if origin_filter != "All":
            filtered = filtered[filtered["origin"] == origin_filter]
        if dest_filter != "All":
            filtered = filtered[filtered["destination"] == dest_filter]

        table_df = filtered[[
            "vehicle_id", "origin", "destination", "current_node",
            "route", "travel_time", "waiting_time", "status"
        ]].rename(columns={
            "vehicle_id": "Vehicle ID",
            "origin": "Origin",
            "destination": "Destination",
            "current_node": "Current position",
            "route": "Route",
            "travel_time": "Travel time (s)",
            "waiting_time": "Waiting time (s)",
            "status": "Status"
        })
        st.dataframe(table_df, width="stretch", height=340, hide_index=True)

        d_left, d_right = st.columns([5, 7])
        with d_left:
            st.markdown("<div class='section-heading'>Vehicle Detail</div>", unsafe_allow_html=True)
            veh_ids = filtered["vehicle_id"].tolist() or df_fleet["vehicle_id"].tolist()
            sel_vid = st.selectbox("Select Vehicle ID", veh_ids)
            veh = engine.fleet_manager.vehicles[sel_vid]
            vd = veh.to_dict()
            prog = veh.progress_ratio if veh.completion_status == "EN_ROUTE" else 1.0 if veh.completion_status == "COMPLETED" else 0.0

            v_pill_bg, v_pill_fg = {
                "EN_ROUTE": (THEME_COLORS["light_surface"], THEME_COLORS["primary_dark"]),
                "WAITING": ("#FCEBEC", THEME_COLORS["alert_coral"]),
                "COMPLETED": (THEME_COLORS["secondary_bg"], THEME_COLORS["accent_primary"]),
            }.get(veh.completion_status, (THEME_COLORS["secondary_bg"], THEME_COLORS["text_secondary"]))
            st.markdown(
                f"<div class='ui-card' style='border-top: 3px solid {THEME_COLORS['accent_primary']};'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                f"<b style='color:{THEME_COLORS['text_primary']};'>{veh.vehicle_id}</b>"
                f"<span class='status-pill' style='background:{v_pill_bg}; color:{v_pill_fg};'>{veh.completion_status}</span></div>"
                f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']}; margin-top:8px;'>Route: <b style='color:{THEME_COLORS['text_primary']};'>{veh.origin} → {veh.destination}</b></div>"
                f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']};'>Current position: <b style='color:{THEME_COLORS['text_primary']};'>{veh.current_node}</b> ({veh.current_road_id or 'At intersection'})</div>"
                f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']};'>Driver profile: <b style='color:{THEME_COLORS['text_primary']};'>{veh.driving_behaviour}</b> · Speed: <b style='color:{THEME_COLORS['text_primary']};'>{vd['current_speed']} km/h</b></div>"
                f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']};'>Travel: <b style='color:{THEME_COLORS['text_primary']};'>{veh.travel_time:.1f} s</b> · Waiting: <b style='color:{THEME_COLORS['text_primary']};'>{veh.waiting_time:.1f} s</b> · Free-flow: <b style='color:{THEME_COLORS['text_primary']};'>{veh.free_flow_travel_time:.1f} s</b></div>"
                f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']};'>Reroutes: <b style='color:{THEME_COLORS['text_primary']};'>{veh.reroute_count}</b> · Toll paid: <b style='color:{THEME_COLORS['text_primary']};'>${veh.toll_paid:.2f}</b> · Progress: <b style='color:{THEME_COLORS['text_primary']};'>{prog*100:.0f}%</b></div>"
                f"</div>",
                unsafe_allow_html=True
            )

        with d_right:
            st.markdown("<div class='section-heading'>Selected Route Map</div>", unsafe_allow_html=True)
            active_roads = []
            for i in range(len(veh.selected_route) - 1):
                r = engine.network.get_road_between(veh.selected_route[i], veh.selected_route[i + 1])
                if r:
                    active_roads.append(r.road_id)
            fig_v = render_city_network_map(
                engine.network, engine.fleet_manager,
                highlight_road_ids=active_roads, show_road_labels=False, height=320
            )
            st.plotly_chart(fig_v, width="stretch", config=PLOTLY_CONFIG, key="veh_route_map")

    with st.expander("Add Custom Vehicle", expanded=False):
        nodes_list = list(engine.network.nodes.keys())
        with st.form("add_custom_vehicle_form"):
            c1, c2, c3, c4 = st.columns(4)
            cid = c1.text_input("Vehicle ID", value=f"VEH_CUSTOM_{len(engine.fleet_manager.vehicles)+1}")
            corig = c2.selectbox("Origin Node", nodes_list, index=0)
            cdest = c3.selectbox("Destination Node", nodes_list, index=min(1, len(nodes_list)-1))
            cbeh = c4.selectbox("Profile", ["NORMAL", "AGGRESSIVE", "CAUTIOUS"])
            if st.form_submit_button("Add Vehicle", type="primary"):
                if corig == cdest:
                    st.error("Origin and Destination must be distinct.")
                else:
                    new_v = engine.fleet_manager.create_custom_vehicle(
                        cid, corig, cdest, cbeh, "travel_time", engine.coordinator.config.enable_pricing
                    )
                    if new_v:
                        st.success(f"Added {cid} ({' -> '.join(new_v.selected_route)})")
                        st.rerun()


# =========================================================
# PAGE 4: COORDINATION
# =========================================================
elif page == "Coordination":
    render_header(
        "AI Coordination",
        "Configure route advisories, congestion pricing, and dynamic lane assignment.",
        f"Preset: {engine.strategy_name}"
    )

    adv_events = engine.coordinator.advisory_system.events
    adv_accepted = sum(1 for e in adv_events if e.accepted)
    price_events = engine.coordinator.pricing_system.events
    active_tolls = sum(1 for r in engine.network.roads.values() if r.toll > 0)
    lane_events = engine.coordinator.lane_system.events

    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown(
            f"<div class='ui-card' style='border-top: 3px solid {THEME_COLORS['accent_primary']};'>"
            f"<div style='font-size:16px; font-weight:600; color:{THEME_COLORS['text_primary']};'>Route Advisories</div>"
            f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']}; margin:6px 0 10px 0;'>Identifies congested links and suggests detours when time savings exceed switching inertia.</div>"
            f"<span class='status-pill' style='background:{THEME_COLORS['light_surface']}; color:{THEME_COLORS['primary_dark']};'>Impact: {len(adv_events)} warnings · {adv_accepted} reroutes</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        engine.coordinator.config.enable_advisories = st.toggle(
            "Enable Route Advisories", value=engine.coordinator.config.enable_advisories,
            help="Allow AI to advise active vehicles around congested bottlenecks."
        )
        engine.coordinator.advisory_system.density_threshold = st.slider(
            "Congestion Threshold", 0.40, 0.95, float(engine.coordinator.advisory_system.density_threshold), 0.05,
            help="Minimum road density required to trigger route warnings."
        )
        engine.coordinator.advisory_system.switch_cost_penalty = st.slider(
            "Switching Penalty (s)", 2.0, 30.0, float(engine.coordinator.advisory_system.switch_cost_penalty), 2.0,
            help="Minimum expected time saving (seconds) before a vehicle accepts a reroute."
        )

    with p2:
        st.markdown(
            f"<div class='ui-card' style='border-top: 3px solid {THEME_COLORS['accent_primary']};'>"
            f"<div style='font-size:16px; font-weight:600; color:{THEME_COLORS['text_primary']};'>Congestion Pricing</div>"
            f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']}; margin:6px 0 10px 0;'>Applies virtual congestion costs to overloaded links to steer price-sensitive vehicles onto bypasses.</div>"
            f"<span class='status-pill' style='background:#FCEBEC; color:{THEME_COLORS['severe_red']};'>Impact: {len(price_events)} toll updates · {active_tolls} tolled roads</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        engine.coordinator.config.enable_pricing = st.toggle(
            "Enable Congestion Pricing", value=engine.coordinator.config.enable_pricing,
            help="Apply virtual dynamic tolls on roads exceeding density thresholds."
        )
        engine.coordinator.pricing_system.base_multiplier = st.slider(
            "Base Virtual Toll ($)", 5.0, 50.0, float(engine.coordinator.pricing_system.base_multiplier), 5.0,
            help="Base virtual toll multiplier scaled non-linearly by congestion excess."
        )
        engine.coordinator.pricing_system.density_threshold = st.slider(
            "Toll Activation Threshold", 0.35, 0.90, float(engine.coordinator.pricing_system.density_threshold), 0.05,
            help="Density threshold above which virtual tolls activate."
        )

    with p3:
        st.markdown(
            f"<div class='ui-card' style='border-top: 3px solid {THEME_COLORS['accent_primary']};'>"
            f"<div style='font-size:16px; font-weight:600; color:{THEME_COLORS['text_primary']};'>Dynamic Lane Assignment</div>"
            f"<div style='font-size:12.5px; color:{THEME_COLORS['text_secondary']}; margin:6px 0 10px 0;'>Reallocates reversible lane capacity toward high-demand directions while conserving total corridor lanes.</div>"
            f"<span class='status-pill' style='background:{THEME_COLORS['secondary_bg']}; color:{THEME_COLORS['primary_dark']};'>Impact: {len(lane_events)} directional shifts</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        engine.coordinator.config.enable_dynamic_lanes = st.toggle(
            "Enable Dynamic Lane Assignment", value=engine.coordinator.config.enable_dynamic_lanes,
            help="Allow reversible lanes to shift toward heavy directional demand."
        )
        engine.coordinator.lane_system.rebalance_interval = st.slider(
            "Rebalancing Interval (Ticks)", 2, 30, int(engine.coordinator.lane_system.rebalance_interval), 1,
            help="Minimum ticks between consecutive lane adjustments on a corridor."
        )
        engine.coordinator.lane_system.ratio_threshold = st.slider(
            "Demand Ratio Threshold", 1.2, 3.0, float(engine.coordinator.lane_system.ratio_threshold), 0.1,
            help="Directional demand ratio required to borrow a reversible lane."
        )

    st.markdown("<div class='section-heading'>Activity Log</div>", unsafe_allow_html=True)
    dec_df = engine.coordinator.get_decision_log_dataframe()
    if not dec_df.empty:
        for d in reversed(dec_df.tail(6).to_dict(orient="records")):
            st.markdown(
                f"<div class='log-entry'>"
                f"<div class='log-meta'>{d['mechanism']} · Tick {d['tick']} · {d['target']} ({d['action']})</div>"
                f"<div>{d['explanation']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.caption("No coordination actions logged yet. Enable mechanisms above and advance the simulation.")

    t1, t2, t3, t4 = st.tabs(["Congested Roads", "Route Advisories", "Virtual Tolls", "Lane Allocations"])
    with t1:
        cong = engine.monitor.get_congested_roads(min_level="MODERATE")
        if cong:
            st.dataframe(pd.DataFrame([c.to_dict() for c in cong]), width="stretch", hide_index=True)
        else:
            st.caption("No congested roads currently detected.")
    with t2:
        df_adv = engine.coordinator.advisory_system.to_dataframe()
        if not df_adv.empty:
            st.dataframe(df_adv, width="stretch", hide_index=True)
        else:
            st.caption("No route advisories recorded.")
    with t3:
        df_pr = engine.coordinator.pricing_system.to_dataframe()
        if not df_pr.empty:
            st.dataframe(df_pr, width="stretch", hide_index=True)
        else:
            st.caption("No virtual toll updates recorded.")
    with t4:
        df_ln = engine.coordinator.lane_system.to_dataframe()
        if not df_ln.empty:
            st.dataframe(df_ln, width="stretch", hide_index=True)
        else:
            st.caption("No lane allocation shifts recorded.")


# =========================================================
# PAGE 5: ANALYTICS
# =========================================================
elif page == "Analytics":
    render_header(
        "Performance Analytics",
        "Evaluate Independent Routing against AI-Coordinated strategies under identical initial conditions.",
        f"Topology: {engine.network.name}"
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        bench_scenario = st.selectbox("Scenario", [SCENARIO_LOW, SCENARIO_NORMAL, SCENARIO_RUSH_HOUR, SCENARIO_UNEVEN], index=2)
    with c2:
        focus_strategy = st.selectbox("Comparison Strategy", ["Combined", "Route Advisories", "Congestion Pricing", "Dynamic Lanes"], index=0)
    with c3:
        bench_vehicles = st.slider("Fleet Size", 15, 90, 50, 5)
    with c4:
        bench_ticks = st.slider("Duration (Ticks)", 80, 250, 180, 20)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Run Single-Seed Benchmark (All 5 Strategies)", type="primary", use_container_width=True):
            with st.spinner("Running 5 strategies under identical seed..."):
                comp = StrategyComparator(network_type=engine.network_type)
                st.session_state.benchmark_result = comp.run_comparison(
                    scenario_name=bench_scenario,
                    vehicle_count=bench_vehicles,
                    max_ticks=bench_ticks,
                    seed=engine.seed,
                    arrival_interval=engine.arrival_interval
                )
    with b2:
        if st.button("Run Multi-Seed Study (5 Seeds: Mean ± Std)", use_container_width=True):
            with st.spinner("Running 25 simulations across 5 seeds..."):
                comp = StrategyComparator(network_type=engine.network_type)
                st.session_state.multi_seed_result = comp.run_multi_seed_comparison(
                    scenario_name=bench_scenario,
                    vehicle_count=bench_vehicles,
                    max_ticks=bench_ticks,
                    seeds=[42, 101, 202, 303, 404],
                    arrival_interval=engine.arrival_interval
                )

    bench_data: Optional[BenchmarkResult] = st.session_state.benchmark_result
    if bench_data:
        m_ind = bench_data.metrics_by_strategy.get("Independent")
        m_foc = bench_data.metrics_by_strategy.get(focus_strategy)
        if m_ind and m_foc:
            st.markdown(f"<div class='section-heading'>Six Core Metrics — Independent vs. {focus_strategy}</div>", unsafe_allow_html=True)
            row1_a, row1_b, row1_c = st.columns(3)
            row2_a, row2_b, row2_c = st.columns(3)
            row1_a.metric("Avg Travel Time (Completed)", f"{m_foc.average_travel_time:.1f} s", f"All-departed: {m_foc.all_departed_avg_time:.1f} s (Indep {m_ind.all_departed_avg_time:.1f} s)", delta_color="off")
            row1_b.metric("Total Journey Time", f"{m_foc.total_travel_time:.0f} s", f"Indep: {m_ind.total_travel_time:.0f} s", delta_color="off")
            row1_c.metric("Traffic Congestion", f"{m_foc.average_density*100:.2f}%", f"Indep: {m_ind.average_density*100:.2f}%", delta_color="off")
            row2_a.metric("Avg Queue Length", f"{m_foc.average_queue_length:.2f}", f"Indep: {m_ind.average_queue_length:.2f}", delta_color="off")
            row2_b.metric("Throughput", f"{m_foc.throughput}/{m_foc.total_vehicles}", f"{m_foc.completion_rate_pct:.1f}% (Indep {m_ind.completion_rate_pct:.1f}%)", delta_color="off")
            row2_c.metric("Average Delay", f"{m_foc.average_delay:.1f} s", f"Indep: {m_ind.average_delay:.1f} s", delta_color="off")

        st.markdown("<div class='section-heading'>Strategy Comparison Table</div>", unsafe_allow_html=True)
        st.dataframe(bench_data.comparison_table, width="stretch", hide_index=True)

        st.markdown("<div class='section-heading'>Relative Improvement vs. Independent</div>", unsafe_allow_html=True)
        st.dataframe(bench_data.improvement_table, width="stretch", hide_index=True)

        ch1, ch2 = st.columns(2)
        with ch1:
            st.plotly_chart(render_strategy_comparison_chart(bench_data.comparison_table), width="stretch", config=PLOTLY_CONFIG, key="an_comp")
            st.markdown("<div class='chart-caption'>Compares completed average travel time, delay, and queue length across all five strategies.</div>", unsafe_allow_html=True)
        with ch2:
            st.plotly_chart(render_travel_time_comparison_chart(bench_data.comparison_table), width="stretch", config=PLOTLY_CONFIG, key="an_tt")
            st.markdown("<div class='chart-caption'>Contrasts completed-only travel time against all-departed travel time (including unfinished vehicles).</div>", unsafe_allow_html=True)

        ch3, ch4 = st.columns(2)
        with ch3:
            st.plotly_chart(render_congestion_comparison_chart(bench_data.comparison_table), width="stretch", config=PLOTLY_CONFIG, key="an_cong")
            st.markdown("<div class='chart-caption'>Displays mean road density alongside average queue length at bottleneck intersections.</div>", unsafe_allow_html=True)
        with ch4:
            st.plotly_chart(render_throughput_comparison_chart(bench_data.comparison_table), width="stretch", config=PLOTLY_CONFIG, key="an_tp")
            st.markdown("<div class='chart-caption'>Shows journey completion percentage within the fixed simulation horizon.</div>", unsafe_allow_html=True)
    else:
        st.caption("Select parameters above and click **Run Single-Seed Benchmark** or **Run Multi-Seed Study**.")

    multi_data: Optional[MultiSeedBenchmarkResult] = st.session_state.multi_seed_result
    if multi_data:
        st.markdown(f"<div class='section-heading'>Multi-Seed Experiment Results ({len(multi_data.seeds)} Seeds — Mean ± Std)</div>", unsafe_allow_html=True)
        st.dataframe(multi_data.summary_table, width="stretch", hide_index=True)
        st.markdown("<div class='chart-caption'>Aggregated mean and standard deviation across repeated random seeds.</div>", unsafe_allow_html=True)


# =========================================================
# PAGE 6: ABOUT
# =========================================================
elif page == "About":
    render_header(
        "About the Project",
        "Multi-Agent Smart City Traffic Flow Simulation · Group 17 · Artificial Intelligence Foundations"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f"<div class='ui-card' style='border-top: 3px solid {THEME_COLORS['accent_primary']};'>"
            f"<div class='section-heading' style='margin-top:0;'>Project Objective</div>"
            f"<p style='color:{THEME_COLORS['text_primary']}; line-height:1.55;'>"
            "When autonomous vehicles select routes independently using greedy shortest-path criteria "
            "(<b>Individual Rationality</b>), traffic concentrates on central corridors and creates bottlenecks. "
            "This application models an urban road network in Python to evaluate how multi-agent AI coordination "
            "mechanisms shift network flow toward <b>Collective Rationality</b>."
            "</p>"
            "<div class='section-heading'>Multi-Agent System Design</div>"
            f"<ul style='color:{THEME_COLORS['text_primary']}; line-height:1.55; padding-left:18px;'>"
            "<li><b>Autonomous Agents:</b> Individual origin, destination, route state, speed, and driver profile (Normal, Aggressive, Cautious).</li>"
            "<li><b>Capacity & Queues:</b> Directed NetworkX road segments enforce capacity limits and FIFO entrance queues.</li>"
            "<li><b>Pathfinding:</b> Dijkstra and A* algorithms supporting distance, travel-time, congestion-aware, and toll-aware costs.</li>"
            "</ul>"
            "</div>",
            unsafe_allow_html=True
        )

    with col_b:
        st.markdown(
            f"<div class='ui-card' style='border-top: 3px solid {THEME_COLORS['primary_dark']};'>"
            f"<div class='section-heading' style='margin-top:0;'>Coordination Mechanisms</div>"
            f"<ol style='color:{THEME_COLORS['text_primary']}; line-height:1.55; padding-left:18px;'>"
            "<li><b>Route Advisories:</b> Broadcasts congestion warnings and suggests detours when time savings exceed switching inertia.</li>"
            "<li><b>Congestion Pricing:</b> Applies virtual Pigouvian tolls on congested links to incentivize bypass routes.</li>"
            "<li><b>Dynamic Lane Assignment:</b> Shifts reversible lanes toward high-demand directions while conserving total road lanes.</li>"
            "</ol>"
            "<div class='section-heading'>Technology Stack</div>"
            f"<p style='color:{THEME_COLORS['text_secondary']}; font-size:13.5px;'>Python 3.14 · NetworkX · NumPy · Pandas · Plotly · Streamlit · pytest</p>"
            "</div>",
            unsafe_allow_html=True
        )

    st.markdown("<div class='section-heading'>System Architecture</div>", unsafe_allow_html=True)
    st.plotly_chart(render_architecture_diagram(), width="stretch", config=PLOTLY_CONFIG, key="about_arch")
