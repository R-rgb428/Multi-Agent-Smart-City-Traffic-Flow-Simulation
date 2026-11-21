"""
Configuration settings for Multi-Agent Smart City Traffic Flow Simulation.
Group 17 - Artificial Intelligence Foundations.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

# UI & Visualization Theme (Mint Mist Palette)
THEME_COLORS = {
    "background": "#EDF6F3",           # Main Pale Mint background
    "secondary_bg": "#E3F0EB",         # Deeper Mint sidebar & secondary surface
    "light_surface": "#D9EDE5",        # Light green surface (pills / active tint)
    "card_bg": "#FFFFFF",              # Clean white cards
    "primary_dark": "#1F3D3A",         # Deep green-grey (primary dark / buttons / active nav)
    "primary_dark_hover": "#162E2C",   # Hover darker green-grey
    "accent_primary": "#34A58A",       # Fresh green primary accent
    "accent_muted": "#5A8F7B",         # Muted green (queued vehicles / secondary green)
    "accent_soft": "#8CC7B8",          # Soft mint green for multi-series charts
    "alert_coral": "#E5484D",          # Coral red (high congestion / alerts / delays)
    "severe_red": "#B8292E",           # Dark red (severe congestion)
    "moderate_orange": "#E87C80",      # Restrained soft coral-red (moderate congestion)
    "text_primary": "#1F3D3A",         # Deep green-grey readable text
    "text_secondary": "#536963",       # High-contrast muted green-grey body text
    "text_muted": "#71847E",           # Muted caption / axis text
    "border": "#D7E6DF",               # Neutral mint border
    "idle_road": "#98A6A1",            # Visible neutral grey for idle roads
    "low_congestion": "#34A58A",       # Free-flow / low congestion green
    "moderate_congestion": "#E87C80",  # Moderate congestion soft coral-red
    "high_congestion": "#E5484D",      # High congestion coral red
    "severe_congestion": "#B8292E",    # Severe congestion dark red
    "road_default": "#98A6A1",
    "node_color": "#FFFFFF",
    "node_border": "#1F3D3A",
    "vehicle_en_route": "#1F3D3A",     # Moving vehicles deep green-grey
    "vehicle_halo": "#34A58A",
    "vehicle_waiting": "#5A8F7B",      # Queued vehicles muted green
    "vehicle_completed": "#34A58A"
}

# Congestion Thresholds (Density = Vehicles / Capacity)
CONGESTION_LEVELS = {
    "LOW": 0.40,
    "MODERATE": 0.70,
    "HIGH": 0.90,
    "SEVERE": 1.00
}

# Simulation Default Parameters
DEFAULT_TIME_STEP = 3.0  # seconds per tick (200 ticks = 600s = 10 min)
DEFAULT_MAX_TICKS = 200
DEFAULT_RANDOM_SEED = 42

# Driver Behavior Profiles
DRIVER_BEHAVIORS = {
    "NORMAL": {
        "speed_factor": 1.0,
        "reroute_sensitivity": 0.5,
        "price_sensitivity": 0.5,
        "patience_ticks": 5
    },
    "AGGRESSIVE": {
        "speed_factor": 1.2,
        "reroute_sensitivity": 0.8,
        "price_sensitivity": 0.2,
        "patience_ticks": 2
    },
    "CAUTIOUS": {
        "speed_factor": 0.85,
        "reroute_sensitivity": 0.3,
        "price_sensitivity": 0.8,
        "patience_ticks": 8
    }
}

# Coordination Default Settings
@dataclass
class CoordinationConfig:
    enable_advisories: bool = False
    enable_pricing: bool = False
    enable_dynamic_lanes: bool = False
    
    # Route advisory params
    advisory_density_threshold: float = 0.60
    advisory_switch_cost_penalty: float = 10.0  # seconds inertia to prevent route flapping
    
    # Congestion pricing params
    pricing_density_threshold: float = 0.50
    pricing_multiplier: float = 20.0  # virtual cost per density excess
    
    # Dynamic lane assignment params
    dynamic_lane_ratio_threshold: float = 1.6  # demand ratio between opposing directions
    lane_rebalance_interval: int = 5  # ticks between checks

# Scenario Configuration Names
SCENARIO_LOW = "Low Traffic"
SCENARIO_NORMAL = "Normal Traffic"
SCENARIO_RUSH_HOUR = "Rush Hour"
SCENARIO_UNEVEN = "Uneven Traffic"
