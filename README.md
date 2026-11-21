# Multi-Agent Smart City Traffic Flow Simulation
### Group 17 — Artificial Intelligence Foundations

A modular, agent-based urban traffic flow simulation built in Python. This project models autonomous vehicles navigating a road network graph and demonstrates how selfish individual routing leads to congestion, while AI-coordinated mechanisms achieve collective network optimization.

---

## 1. Project Overview

In urban traffic networks, drivers traditionally act with **Individual Rationality**: each driver independently selects the route that minimizes their personal travel time based on individual information. When many vehicles make this selfish choice simultaneously, traffic concentrates on the shortest corridors, causing severe bottlenecks, long queues, and wasted time (a phenomenon known in game theory as the **Price of Anarchy** and **Braess's Paradox**).

This project implements an intelligent Multi-Agent System (MAS) comparing:
1. **Independent Vehicle Routing:** Baseline uncoordinated greedy navigation.
2. **AI-Coordinated Vehicle Routing:** Network-wide coordination through:
   - **Route Advisories:** Dynamic bottleneck warnings and alternative route suggestions with switching inertia penalties.
   - **Congestion Pricing:** Virtual Pigouvian tolls on overloaded roads to internalize the congestion externality.
   - **Dynamic Lane Assignment:** Reversible lane borrowing that shifts capacity toward heavy directional surges while conserving total road space.
   - **Combined Coordination:** Integration of all three mechanisms.

---

## 2. Key Features

- **NetworkX Road Graph:** Intersections as nodes, directed road segments as edges with lengths, capacities, densities, dynamic speeds, queues, and tolls.
- **Autonomous Vehicle Agents:** Each vehicle is an intelligent agent with unique ID, origin, destination, current position, speed, route history, and behavioral profile (Normal, Aggressive, Cautious).
- **Physical Capacity Constraints:** Discrete-time simulation engine enforcing strict capacity limits without teleportation. Vehicles queue at intersections when roads are full.
- **Routing Algorithms:** Dijkstra and A* (Euclidean heuristic) pathfinding supporting shortest distance, estimated travel time, and congestion-aware cost functions.
- **Explainable AI (XAI) Logging:** Every coordination intervention is recorded with human-readable rationale ("Why the AI made this decision").
- **Reproducible Benchmarking:** Identical random seeds and initial vehicle origin-destination assignments across all five strategies.
- **Interactive Streamlit Dashboard:** Dark navy / charcoal UI featuring an interactive Plotly city map, live vehicle markers, telemetry tables, and analytical charts.

---

## 3. System Architecture

```
smart_city_traffic/
│
├── app.py                      # Interactive Streamlit Web Application (6 Pages)
├── main.py                     # CLI Runner, Headless Benchmarking & Test Runner
├── config.py                   # Centralized configuration, colors, and thresholds
├── requirements.txt            # Python dependencies
├── README.md                   # Comprehensive documentation
│
├── road_network/               # Module 1: Road Network
│   ├── __init__.py
│   ├── network.py              # Intersection & RoadSegment dataclasses, RoadNetwork DiGraph
│   └── scenarios.py            # Predefined topologies (Smart City 12-node & Arterial 6-node)
│
├── agents/                     # Module 2: Vehicle Agent System
│   ├── __init__.py
│   ├── vehicle.py              # Autonomous VehicleAgent state machine & movement rules
│   └── vehicle_manager.py      # Fleet lifecycle, scenario generation, bulk updates
│
├── routing/                    # Module 3: Route Selection
│   ├── __init__.py
│   └── route_planner.py        # Dijkstra, A*, multi-criteria cost functions, comparisons
│
├── monitoring/                 # Module 4: Traffic Monitoring
│   ├── __init__.py
│   └── traffic_monitor.py      # Telemetry collector, density/speed calculation, bottlenecks
│
├── coordination/               # Module 5: AI Coordination
│   ├── __init__.py
│   ├── route_advisory.py       # Mechanism A: Dynamic warnings & rerouting advice
│   ├── congestion_pricing.py   # Mechanism B: Dynamic Pigouvian virtual tolls
│   ├── dynamic_lane.py         # Mechanism C: Reversible lane borrowing
│   └── coordinator.py          # Unified master coordinator & XAI logger
│
├── simulation/                 # Module 6: Simulation Engine
│   ├── __init__.py
│   └── engine.py               # Discrete-time simulation clock & lifecycle controls
│
├── evaluation/                 # Performance Evaluation & Benchmarking
│   ├── __init__.py
│   ├── metrics.py              # 6 Core traffic parameters calculation
│   └── comparison.py           # Multi-strategy benchmark runner & % improvements
│
├── visualization/              # Visualization Components
│   ├── __init__.py
│   ├── city_map.py             # Interactive Plotly 2D city map with offset lanes
│   └── charts.py               # Time-series, speed-density curves, radar & bar charts
│
└── tests/                      # Automated Unit Test Suite (pytest)
    ├── test_network.py         # Tests for graph connectivity & capacities
    ├── test_agents.py          # Tests for vehicle movement & queueing
    ├── test_routing.py         # Tests for Dijkstra, A*, and alternatives
    ├── test_monitoring.py      # Tests for real-time telemetry & snapshots
    ├── test_coordination.py    # Tests for advisories, pricing, lanes & presets
    ├── test_simulation.py      # Tests for simulation clock & lifecycle
    ├── test_evaluation.py      # Tests for metrics & benchmark comparison
    └── test_visualization.py   # Tests for Plotly map & chart generation
```

---

## 4. The Six Core Evaluation Parameters

The project measures and evaluates network performance using six parameters derived from actual simulation runs:

1. **Average Travel Time ($\bar{T}$):** Mean seconds elapsed for completed vehicles to travel from origin to destination:
   $$\bar{T} = \frac{1}{|V_{\text{completed}}|} \sum_{v \in V_{\text{completed}}} T_v$$
2. **Total Travel Time ($\sum T_i$):** Cumulative travel seconds expended by the entire fleet across the simulation.
3. **Traffic Congestion (Density):** Mean ratio of vehicles to road capacity across network segments ($\rho = N / C$), categorized as:
   - **Low:** $\rho < 40\%$ (Green)
   - **Moderate:** $40\% \le \rho < 70\%$ (Yellow)
   - **High:** $70\% \le \rho < 90\%$ (Orange)
   - **Severe:** $\rho \ge 90\%$ (Red)
4. **Queue Length:** Average and peak number of vehicles waiting at intersections due to saturated downstream links.
5. **Throughput:** Number of vehicles that successfully reach their destination within the simulation timeframe, and the completion percentage ($N_{\text{completed}} / N_{\text{total}}$).
6. **Average Delay:** Additional travel time incurred due to congestion compared to the theoretical free-flow baseline ($T_v - T_{\text{free\_flow}}$).

---

## 5. Installation & Setup

### Prerequisites
- Python 3.11 or newer (compatible with Python 3.11, 3.12, 3.13, 3.14).
- Operating System: Windows, macOS, or Linux.

### Setup Instructions (Windows)

1. Open PowerShell or Command Prompt and navigate to the project directory:
   ```powershell
   cd c:\Users\RUSHIL\Desktop\AI276
   ```

2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```

---

## 6. How to Run the Application

### Option A: Interactive Streamlit Dashboard (Recommended)
Launch the full multi-page visual dashboard:
```powershell
streamlit run app.py
```
Or:
```powershell
python -m streamlit run app.py
```
Open your browser to `http://localhost:8501`.

### Option B: Command Line Interface (CLI)
Run a headless benchmark and display terminal comparison tables:
```powershell
python main.py --vehicles 35 --ticks 120 --scenario "Normal Traffic"
```

To run the automated test suite via CLI:
```powershell
python main.py --test
```

---

## 7. Dashboard Guide (6 Pages)

| Page | Description |
|---|---|
| **1. Overview Dashboard** | Executive summary with KPI metric cards, high-level city map, congestion breakdown, and critical bottleneck table. |
| **2. City Traffic Simulation** | Live interactive Plotly map. Play, Pause, Step (1 tick), Advance (10 ticks), Reset, or enable continuous auto-run. Live road telemetry table. |
| **3. Vehicle Management** | Filterable fleet table, individual agent inspector with route progress bar and highlighted map path, and a custom vehicle deployment form. |
| **4. AI Coordination** | Parameter sliders for advisories, pricing, and dynamic lanes. Real-time Explainable AI (XAI) decision stream showing why the AI intervened. |
| **5. Performance Analysis** | One-click comparative evaluation runner executing all 5 strategies under identical random seeds. Displays numerical tables, % improvements, bar charts, and radar plots. |
| **6. About the Project** | Detailed project documentation, Multi-Agent System concepts, Game Theory analysis (User Equilibrium vs System Optimum), and architecture diagram. |

---

## 8. Predefined Traffic Scenarios

1. **Low Traffic:** 15-20 vehicles, dispersed demand, zero congestion, free-flow speeds.
2. **Normal Traffic:** 35-50 vehicles, standard commute distribution across residential and commercial zones.
3. **Rush Hour:** 60-100 vehicles, heavy directional commute from residential suburbs into Downtown and Financial Core, creating severe bridge bottlenecks.
4. **Uneven Traffic:** Heavy concentration where 85%+ of vehicles target a single destination (Downtown Core).

---

## 9. Running Tests

Run the complete test suite with verbose output:
```powershell
python -m pytest -v tests/
```
All 23 automated unit tests cover:
- Graph topology and road capacity constraints
- Dijkstra and A* pathfinding accuracy
- Vehicle agent lifecycle, progression, and queue handling
- Route advisory generation and inertia thresholds
- Dynamic Pigouvian toll adjustments
- Directional reversible lane conservation invariants
- Discrete-time simulation engine state transitions
- Metric calculations and comparative benchmarking
- Plotly map and analytical chart generation
