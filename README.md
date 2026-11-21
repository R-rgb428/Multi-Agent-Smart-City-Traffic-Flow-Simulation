# Multi-Agent Smart City Traffic Flow Simulation

### Group 17 — Artificial Intelligence Foundations

A modular, agent-based urban traffic simulation built in Python. This project models autonomous vehicles navigating a road network and demonstrates how independent routing decisions can contribute to congestion, while coordinated traffic-management mechanisms aim to improve overall network efficiency.

<p align="center">
  <a href="https://smart-city-traffic-simulation.streamlit.app/"><strong>Live Application</strong></a>
</p>

---

## 1. Project Overview

In urban traffic networks, drivers traditionally act with **Individual Rationality**: each driver independently selects the route that minimizes their personal travel time based on individual information. When many vehicles make similar decisions simultaneously, traffic concentrates on the same corridors, causing bottlenecks, long queues and wasted time. This relates to game-theoretic concepts such as the **Price of Anarchy** and **Braess's Paradox**.

This project implements a Multi-Agent System (MAS) that compares independent vehicle routing with coordinated traffic-management strategies.

The system implements five strategies:

1. **Independent Vehicle Routing:** Baseline uncoordinated routing where vehicles make individual route decisions.
2. **Route Advisories:** Dynamic bottleneck warnings and alternative route suggestions with switching inertia penalties.
3. **Congestion Pricing:** Virtual Pigouvian tolls on overloaded roads to account for congestion externalities.
4. **Dynamic Lane Assignment:** Reversible lane borrowing that shifts capacity toward heavy directional demand while conserving total road space.
5. **Combined Coordination:** Integration of route advisories, congestion pricing and dynamic lane assignment.

## 2. Key Features

- **NetworkX Road Graph:** Intersections as nodes and directed road segments as edges, with lengths, capacities, densities, dynamic speeds, queues and tolls.
- **Autonomous Vehicle Agents:** Each vehicle has a unique ID, origin, destination, current position, speed, route history and behavioural profile (Normal, Aggressive or Cautious).
- **Physical Capacity Constraints:** Discrete-time simulation engine enforcing road capacity limits. Vehicles queue at intersections when downstream roads are full.
- **Routing Algorithms:** Dijkstra and A* pathfinding supporting shortest-distance, estimated-travel-time and congestion-aware cost functions.
- **Explainable AI (XAI) Logging:** Coordination interventions are recorded with human-readable explanations of why decisions were made.
- **Reproducible Benchmarking:** Identical random seeds and initial vehicle origin-destination assignments across all five strategies.
- **Interactive Streamlit Dashboard:** Light mint-themed interface featuring interactive Plotly road-network visualizations, vehicle monitoring, simulation controls and analytical charts.

## 3. System Architecture

The project follows a modular architecture:

```text
Multi-Agent-Smart-City-Traffic-Flow-Simulation/
│
├── app.py                      # Interactive Streamlit Web Application
├── main.py                     # CLI Runner, Benchmarking and Test Runner
├── config.py                   # Centralized configuration and thresholds
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
│
├── road_network/               # Road Network
│   ├── network.py              # Intersections, road segments and graph
│   └── scenarios.py            # Predefined network topologies
│
├── agents/                     # Vehicle Agent System
│   ├── vehicle.py              # Autonomous vehicle behaviour
│   └── vehicle_manager.py      # Fleet lifecycle and management
│
├── routing/                    # Route Selection
│   └── route_planner.py        # Dijkstra, A* and cost functions
│
├── monitoring/                 # Traffic Monitoring
│   └── traffic_monitor.py      # Telemetry and congestion detection
│
├── coordination/               # AI Coordination
│   ├── route_advisory.py       # Dynamic route recommendations
│   ├── congestion_pricing.py   # Virtual congestion pricing
│   ├── dynamic_lane.py         # Reversible lane assignment
│   └── coordinator.py          # Master coordination system and XAI
│
├── simulation/                 # Simulation Engine
│   └── engine.py               # Simulation clock and lifecycle
│
├── evaluation/                 # Performance Evaluation
│   ├── metrics.py              # Traffic performance metrics
│   └── comparison.py           # Strategy benchmarking
│
├── visualization/              # Visualization Components
│   ├── city_map.py             # Interactive Plotly road map
│   └── charts.py               # Analytical charts and graphs
│
└── tests/                      # Automated Unit Tests
    ├── test_network.py
    ├── test_agents.py
    ├── test_routing.py
    ├── test_monitoring.py
    ├── test_coordination.py
    ├── test_simulation.py
    ├── test_evaluation.py
    └── test_visualization.py
```

## 4. Core Evaluation Parameters

The project measures network performance using six parameters:

1. **Average Travel Time (\(\bar{T}\)):** Mean time taken by completed vehicles to travel from origin to destination.

   \[
   \bar{T} = \frac{1}{|V_{\text{completed}}|}
   \sum_{v \in V_{\text{completed}}} T_v
   \]

2. **Total Travel Time (\(\sum T_i\)):** Cumulative travel time expended by the entire vehicle fleet.

3. **Traffic Congestion (Density):** Ratio of vehicles to road capacity across network segments.

   \[
   \rho = \frac{N}{C}
   \]

   Congestion categories:
   - **Low:** \(\rho < 40\%\)
   - **Moderate:** \(40\% \leq \rho < 70\%\)
   - **High:** \(70\% \leq \rho < 90\%\)
   - **Severe:** \(\rho \geq 90\%\)

4. **Queue Length:** Average and peak number of vehicles waiting at intersections due to saturated downstream roads.

5. **Throughput:** Number of vehicles reaching their destinations within the simulation timeframe, including completion percentage.

   \[
   \text{Completion Rate} =
   \frac{N_{\text{completed}}}{N_{\text{total}}}
   \times 100
   \]

6. **Average Delay:** Additional travel time incurred due to congestion compared with the theoretical free-flow baseline.

   \[
   \text{Delay} = T_v - T_{\text{free-flow}}
   \]

## 5. Installation and Setup

### Prerequisites

- Python 3.11 or newer.
- Git.
- Windows, macOS or Linux.

### Step 1: Clone the repository

```bash
git clone https://github.com/R-rgb428/Multi-Agent-Smart-City-Traffic-Flow-Simulation.git
```

### Step 2: Navigate to the project directory

```bash
cd Multi-Agent-Smart-City-Traffic-Flow-Simulation
```

### Step 3: Create a virtual environment (recommended)

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

### Step 4: Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 6. Running the Application

### Option A: Interactive Streamlit Dashboard

Launch the full interactive dashboard:

```bash
streamlit run app.py
```

Alternatively:

```bash
python -m streamlit run app.py
```

Open the application locally at:

`http://localhost:8501`

### Option B: Command-Line Interface

Run a headless simulation benchmark:

```bash
python main.py --vehicles 35 --ticks 120 --scenario "Normal Traffic"
```

### Option C: Run Automated Tests

Execute the complete test suite:

```bash
python -m pytest -v tests/
```

Alternatively, use:

```bash
python main.py --test
```

## 7. Dashboard Guide

The interactive dashboard provides six main sections:

| Section | Description |
|---|---|
| **Overview** | Network health, KPI summary, congestion breakdown and traffic status. |
| **Live Simulation** | Interactive road network, vehicle movement and simulation controls. |
| **Vehicles** | Vehicle fleet information, individual vehicle inspection and monitoring. |
| **Coordination** | Coordination strategies, configuration and Explainable AI decision information. |
| **Analytics** | Performance metrics, comparative evaluation and analytical visualizations. |
| **About** | Project documentation, architecture and system information. |

## 8. Predefined Traffic Scenarios

The simulation supports four predefined traffic scenarios:

1. **Low Traffic:** 15–20 vehicles, dispersed demand and relatively free-flow conditions.
2. **Normal Traffic:** 35–50 vehicles, representing standard commuting demand across residential and commercial areas.
3. **Rush Hour:** 60–100 vehicles, with heavy directional demand from residential areas toward Downtown and the Financial Core.
4. **Uneven Traffic:** Heavy concentration where more than 85% of vehicles target a single destination (Downtown Core).

## 9. Automated Testing

The project includes 23 automated unit tests covering:

- Road-network connectivity and capacity constraints.
- Dijkstra and A* pathfinding accuracy.
- Vehicle movement, lifecycle and queue handling.
- Route advisory generation and switching inertia.
- Dynamic congestion pricing.
- Reversible lane capacity conservation.
- Simulation engine state transitions.
- Performance metrics and benchmark comparisons.
- Plotly map and chart generation.

Run the tests using:

```bash
python -m pytest -v tests/
```

## 10. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core implementation |
| Streamlit | Interactive web dashboard |
| NetworkX | Graph-based road-network modelling |
| NumPy | Numerical computation |
| Pandas | Data processing |
| Plotly | Interactive visualizations |
| Matplotlib | Supporting visualizations |
| SciPy | Scientific computing |
| Pytest | Automated testing |

## 11. Project Objectives

The project explores the application of Multi-Agent Systems and game-theoretic concepts to urban traffic management.

Its objectives are to:

- Model autonomous decision-making in a shared road network.
- Demonstrate how individual routing decisions can contribute to system-wide congestion.
- Implement coordination mechanisms that influence vehicle routing and road capacity.
- Compare independent and coordinated traffic-management strategies.
- Evaluate network performance using measurable traffic parameters.

## 12. Contributors

**Group 17 — Artificial Intelligence Foundations**

Developed as an academic project.

## 13. License

No open-source license has been specified for this repository. All rights are reserved by default unless a license is added.
