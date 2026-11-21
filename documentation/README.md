# Documentation — Multi-Agent Smart City Traffic Flow Simulation (Group 17)

Welcome to the documentation suite for **Group 17 — Artificial Intelligence Foundations: Multi-Agent Smart City Traffic Flow Simulation**. Every file in this folder is verified directly against the source code and experimental outputs in the repository.

---

## Documentation Deliverables

1. **[COMPLETE_PROJECT_DOCUMENTATION.pdf](./COMPLETE_PROJECT_DOCUMENTATION.pdf)**
   - Master conceptual and engineering report covering project motivation, Multi-Agent Systems, end-to-end simulation lifecycle, `VehicleAgent` internals, network topologies & mathematical formulas, all 5 traffic strategies, 10-seed benchmark analysis (`data/final_benchmark_summary_10seeds.csv`), technology stack, module dependency map, `pytest` validation, Windows setup, and honest limitations.
2. **[USER_OPERATION_MANUAL.pdf](./USER_OPERATION_MANUAL.pdf)**
   - Step-by-step website operation guide with live high-resolution screenshots of all six Streamlit pages (`Overview`, `Live Simulation`, `Vehicles`, `Coordination`, `Analytics`, `About`), explaining every sidebar setting, slider, button, KPI card, insight banner, chart, and troubleshooting step.
3. **[PROJECT_VIVA_PREPARATION.pdf](./PROJECT_VIVA_PREPARATION.pdf)**
   - Oral defense handbook including a 2-minute pitch, a 5-minute presentation script, *"If the Examiner Points at Any Website Element"* instant answers, 105 graded technical Q&As (30 Basic, 30 Intermediate, 20 Advanced, 15 Code Implementation, 10 Evaluator Challenge Questions), and a 1-page formula cheat sheet.
4. **[PROJECT_GLOSSARY.pdf](./PROJECT_GLOSSARY.pdf)**
   - Alphabetical dictionary (Simple Meaning, Technical Meaning, Where Used) plus a comparison matrix distinguishing similar terms (*Travel Time vs Waiting Time vs Delay*, *Traffic Density vs Network Occupancy*, *Throughput vs Total Fleet*, *Completed-Only vs All-Departed Averages*).

---

## Quick Installation & Execution (Windows)

### 1. Prerequisites
- Python 3.11 or newer (verified on Python 3.14.2)

### 2. Install Dependencies
```powershell
cd c:\Users\RUSHIL\Desktop\AI276
python -m pip install -r requirements.txt
```

### 3. Run the Interactive Web Dashboard (Streamlit)
```powershell
python -m streamlit run app.py
```
Then open `http://localhost:8501` in your browser. Press `Ctrl + C` in the terminal to stop the server.

### 4. Run Automated Tests (`pytest`)
```powershell
python -m pytest -v
```

### 5. Run Headless CLI Benchmark
```powershell
python main.py --scenario "Rush Hour" --vehicles 50 --ticks 180
```
