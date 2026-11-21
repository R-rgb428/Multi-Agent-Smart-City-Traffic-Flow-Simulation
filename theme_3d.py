"""
theme_3d.py - Mint Mist visual theme for the Smart City Streamlit dashboard.

Uses centralized color tokens from config.THEME_COLORS so backgrounds, cards,
navigation, charts, and traffic states remain consistent across all six pages.

Usage (right after st.set_page_config):

    from theme_3d import inject_3d_theme
    inject_3d_theme()
"""
import streamlit as st
from config import THEME_COLORS

_CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  --mint-bg:         {background};
  --mint-sidebar:    {secondary_bg};
  --mint-light:      {light_surface};
  --card-bg:         {card_bg};
  --dark:            {primary_dark};
  --dark-hover:      {primary_dark_hover};
  --green:           {accent_primary};
  --green-muted:     {accent_muted};
  --coral:           {alert_coral};
  --severe:          {severe_red};
  --orange:          {moderate_orange};
  --idle:            {idle_road};
  --text-main:       {text_primary};
  --text-sec:        {text_secondary};
  --text-muted:      {text_muted};
  --border:          {border};

  /* Restrained shadows */
  --shadow-sm: 0 1px 2px rgba(31, 61, 58, .04), 0 2px 6px rgba(31, 61, 58, .04);
  --shadow-md: 0 2px 4px rgba(31, 61, 58, .05), 0 6px 16px rgba(31, 61, 58, .06);
}}

html, body, [class*="css"], .stApp {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  color: var(--text-main);
}}

/* ---------- prevent Streamlit fragment stale-opacity blinking / pulsing ---------- */
[data-stale="true"],
div[data-stale="true"],
.element-container,
div[data-testid="stElementContainer"] {{
  opacity: 1 !important;
  transition: none !important;
}}

/* ---------- custom live SVG map card ---------- */
iframe[title*="smart_city_live_map"],
div[data-testid="stCustomComponentV1"] iframe {{
  background: var(--card-bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  box-shadow: var(--shadow-sm) !important;
}}

/* ---------- main canvas: pale mint ---------- */
.stApp {{
  background-color: var(--mint-bg);
}}
header[data-testid="stHeader"] {{
  background: rgba(237, 246, 243, 0.92) !important;
}}

.block-container {{
  padding-top: 2.8rem !important;
  padding-bottom: 2.25rem !important;
  max-width: 1420px;
}}

/* ---------- sidebar: slightly deeper pale mint ---------- */
section[data-testid="stSidebar"] {{
  background-color: var(--mint-sidebar);
  border-right: 1px solid var(--border);
  box-shadow: 2px 0 12px rgba(31, 61, 58, .04);
}}
section[data-testid="stSidebar"] .block-container {{
  padding-top: 1.25rem !important;
  padding-bottom: 1.25rem !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button {{
  justify-content: flex-start !important;
  text-align: left !important;
  border-radius: 10px !important;
  margin-bottom: 2px;
}}

/* Inactive navigation items: light white surface with dark text */
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] {{
  background: var(--card-bg) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-main) !important;
  box-shadow: var(--shadow-sm) !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"]:hover {{
  background: var(--mint-light) !important;
  border-color: var(--green) !important;
}}

/* Active navigation item: deep green-grey with white text & fresh green indicator */
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {{
  background: var(--dark) !important;
  color: #FFFFFF !important;
  text-shadow: none !important;
  border: 1px solid var(--dark) !important;
  border-left: 4px solid var(--green) !important;
  font-weight: 700 !important;
  box-shadow: var(--shadow-sm) !important;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"]:hover {{
  background: var(--dark-hover) !important;
  border-color: var(--dark-hover) !important;
  border-left: 4px solid var(--green) !important;
}}

/* ---------- KPI cards & content panels (uniform white + restrained borders) ---------- */
div[data-testid="stMetric"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stMetric"]),
.ui-card {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow .15s ease, border-color .15s ease;
  position: relative;
  overflow: hidden;
}}
div[data-testid="stMetric"]::before {{
  content: "";
  position: absolute; left: 0; top: 0; bottom: 0; width: 3.5px;
  background: var(--green);
  border-radius: 12px 0 0 12px;
}}

div[data-testid="stMetric"]:hover,
.ui-card:hover {{
  box-shadow: var(--shadow-md);
  border-color: #C2DBD1;
}}
div[data-testid="stMetricLabel"] {{
  text-transform: uppercase;
  letter-spacing: .05em;
  font-size: .72rem;
  font-weight: 600;
  color: var(--text-sec) !important;
  opacity: 1 !important;
}}
div[data-testid="stMetricValue"] {{
  font-size: clamp(1.3rem, 1.85vw, 1.82rem);
  font-weight: 700;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
div[data-testid="stMetricDelta"] {{
  font-size: .76rem;
  color: var(--text-muted);
  white-space: nowrap;
}}

/* ---------- buttons & simulation controls ---------- */
/* Secondary buttons (Pause, Resume, Step, Reset, etc.): light neutral surface with dark text */
.stButton > button,
button[data-testid^="stBaseButton"] {{
  border-radius: 10px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: var(--card-bg);
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
  transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease, background .12s ease;
}}
.stButton > button:hover,
button[data-testid^="stBaseButton"]:hover {{
  background: var(--mint-light);
  border-color: var(--green);
  box-shadow: var(--shadow-md);
}}
.stButton > button:active,
button[data-testid^="stBaseButton"]:active {{
  transform: translateY(1px);
  box-shadow: inset 0 1px 2px rgba(31, 61, 58, .12);
}}
.stButton > button:focus-visible,
button[data-testid^="stBaseButton"]:focus-visible {{
  outline: 2px solid var(--green);
  outline-offset: 2px;
}}
.stButton > button:disabled,
button[data-testid^="stBaseButton"]:disabled {{
  opacity: 1 !important;
  background: #E9F2EE !important;
  border: 1px solid #C9DCD4 !important;
  color: #58706A !important;
  box-shadow: none !important;
  cursor: not-allowed !important;
}}
.stButton > button:disabled *,
button[data-testid^="stBaseButton"]:disabled * {{
  color: inherit !important;
  opacity: 1 !important;
}}

/* Primary actions (Start, Apply & Reset, Run Benchmark, Add Vehicle): deep green-grey */
.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {{
  color: #FFFFFF !important;
  border: 1px solid var(--dark) !important;
  background: var(--dark) !important;
  box-shadow: var(--shadow-sm) !important;
}}
.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {{
  background: var(--dark-hover) !important;
  border-color: var(--dark-hover) !important;
  box-shadow: var(--shadow-md) !important;
}}
button[data-testid="stBaseButton-primary"]:disabled,
.stButton > button[kind="primary"]:disabled {{
  opacity: 1 !important;
  background: #8FA6A0 !important;
  border: 1px solid #829993 !important;
  color: #FFFFFF !important;
  box-shadow: none !important;
  cursor: not-allowed !important;
}}

/* ---------- inputs & dropdowns ---------- */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea {{
  background: var(--card-bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text-main) !important;
  box-shadow: inset 0 1px 2px rgba(31, 61, 58, .03);
  transition: box-shadow .15s ease, border-color .15s ease;
}}
div[data-baseweb="select"] > div:hover,
div[data-baseweb="input"] > div:focus-within {{
  border-color: var(--green) !important;
  box-shadow: 0 0 0 3px rgba(52, 165, 138, .16);
}}

/* ---------- banners, chart containers, expanders & tabs ---------- */
div[data-testid="stAlert"] {{
  background: var(--mint-light);
  border: 1px solid var(--border);
  border-left: 4px solid var(--green);
  border-radius: 11px;
  box-shadow: var(--shadow-sm);
  color: var(--text-main);
}}

div[data-testid="stPlotlyChart"],
div[data-testid="stDeckGlJsonChart"],
div[data-testid="stVegaLiteChart"] {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 8px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow .18s ease, border-color .18s ease;
}}
div[data-testid="stPlotlyChart"]:hover {{
  border-color: #C2DBD1;
  box-shadow: var(--shadow-md);
}}

div[data-testid="stDataFrame"],
details[data-testid="stExpander"] {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
}}
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlock"] > div[data-testid="stLayoutWrapper"] {{
  border-radius: 12px;
}}

button[data-baseweb="tab"] {{
  color: var(--text-sec) !important;
  font-weight: 600 !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
  color: var(--dark) !important;
  background: var(--mint-light);
  border-radius: 9px 9px 0 0;
}}

/* ---------- headings & typography ---------- */
h1, h2, h3 {{ letter-spacing: -.015em; font-weight: 700; color: var(--text-main); }}
.page-title {{
  font-size: 26px; font-weight: 700; color: var(--text-main);
  letter-spacing: -0.02em; margin: 0 0 2px 0; line-height: 1.25;
}}
.page-subtitle {{
  font-size: 14px; color: var(--text-sec); margin: 0 0 12px 0; line-height: 1.45;
}}
.section-heading {{
  font-size: 16.5px; font-weight: 600; color: var(--text-main); margin: 14px 0 8px 0;
}}

/* ---------- status pill, health summary & insight banner ---------- */
.status-pill {{
  display: inline-flex; align-items: center; gap: 7px;
  padding: 5px 12px; border-radius: 999px;
  font-size: 12px; font-weight: 600; white-space: nowrap;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}}
.status-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.dist-bar {{
  display: flex; height: 11px; width: 100%; border-radius: 6px;
  overflow: hidden; background-color: var(--mint-bg); margin: 10px 0 14px 0;
  border: 1px solid var(--border);
}}
.health-row {{
  display: flex; justify-content: space-between; align-items: center;
  font-size: 13px; padding: 5px 0; color: var(--text-main);
}}
.health-stat-chip {{
  display: flex; justify-content: space-between; align-items: center;
  background: var(--mint-bg); border: 1px solid var(--border);
  border-radius: 9px; padding: 6px 10px; margin-top: 6px;
  font-size: 12.5px;
}}
.insight-line {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-left: 4px solid var(--green);
  border-radius: 11px;
  padding: 10px 14px;
  margin: 10px 0 14px 0;
  font-size: 13.5px;
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
}}
.insight-line.alert {{
  background: var(--card-bg);
  border-left-color: var(--coral);
}}
.log-entry {{
  background: var(--card-bg); border: 1px solid var(--border);
  border-left: 4px solid var(--green); border-radius: 10px;
  padding: 10px 14px; margin-bottom: 8px; font-size: 13.5px;
  box-shadow: var(--shadow-sm);
}}
.log-meta {{ font-size: 12px; font-weight: 600; color: var(--text-sec); margin-bottom: 2px; }}
.chart-caption {{ font-size: 12px; color: var(--text-muted); padding: 4px 2px 10px 2px; }}

/* ---------- progress bar: fresh green ---------- */
div[data-testid="stProgress"] > div > div > div {{
  background: var(--green);
  border-radius: 999px;
}}

/* ---------- responsive narrow window (~800px) ---------- */
@media (max-width: 900px) {{
  .block-container {{ padding-top: 2.2rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }}
  div[data-testid="stMetricValue"] {{ font-size: 1.25rem !important; }}
  .stButton > button, button[data-testid^="stBaseButton"] {{
    padding-left: 8px !important;
    padding-right: 8px !important;
    font-size: 12.5px !important;
  }}
  .page-title {{ font-size: 22px; }}
}}

/* ---------- respect reduced-motion ---------- */
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; }}
}}
</style>
"""


def inject_3d_theme() -> None:
    """Call once per run, after st.set_page_config()."""
    css = _CSS_TEMPLATE.format(**THEME_COLORS)
    st.markdown(css, unsafe_allow_html=True)
