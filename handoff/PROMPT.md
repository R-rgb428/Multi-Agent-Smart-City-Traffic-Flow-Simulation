# Paste this into Antigravity

Before pasting: open your existing Smart City project in Antigravity, then copy this whole `handoff/` folder into the project root (so you have `handoff/reference`, `handoff/DESIGN_SPEC.md`, `handoff/api-contract.md`). Use **Planning mode** so it shows a plan before editing.

---

```
You are upgrading my "Smart City - Traffic Intelligence" project. It is currently a
Python app with a Streamlit UI (Plotly road map, KPI cards, sidebar settings) that runs
an autonomous-vehicle traffic simulation on a 12-node road network (38 road segments,
516 slots, strategies such as "Independent", seeded scenarios, 200-300 ticks).

GOAL
Replace the Streamlit UI with a modern, light-theme, slightly-3D web dashboard that
matches the reference in /handoff, while KEEPING the simulation logic exactly as it is.

THE REFERENCE (read these first, in this order)
1. handoff/reference/index.html + styles.css + app.js   -> the exact target look.
   Open index.html in the browser and screenshot it. This is ground truth for visuals.
2. handoff/DESIGN_SPEC.md                               -> tokens, layout, components,
   map rendering rules, accessibility bar. Follow it.
3. handoff/api-contract.md                              -> JSON the frontend expects
   from the Python backend.
All numbers in the reference are SAMPLE data. Real data must come from the simulation.

TARGET ARCHITECTURE
- Backend: FastAPI wrapper around my existing simulation (import it, do not rewrite it).
  Implement the endpoints in api-contract.md. CORS for http://localhost:5173.
- Frontend: Vite + React + TypeScript + Tailwind CSS (I already use this stack in other
  projects). Put it in /web. Port the reference CSS tokens into tailwind.config / a
  tokens.css, and keep the reference class names as components where that is simpler than
  Tailwind utilities (the shadows and gradients are easier as CSS than as utility soup).
- Keep the old Streamlit app working, untouched, in place until the new UI reaches parity.
  Do not delete it.

WORK IN PHASES. Stop after each phase and show me what changed. Do not start the next
phase until the current one runs without errors.

PHASE 0 - Understand (no edits)
- Read the project and write a short plan: where the simulation lives, how a tick runs,
  what state it exposes (vehicles, roads, intersections, KPIs, strategies), how the
  Streamlit app calls it, and where each field in api-contract.md will come from.
- List any field in the contract the simulation cannot supply yet, and how you will
  produce it (see "Decisions" below). Ask me only if something is truly ambiguous.

PHASE 1 - Backend API
- Create /api with FastAPI. Endpoints from api-contract.md: configure, start, pause,
  reset, step, state, decisions, oversight, activity.
- Run the simulation in a background task/thread guarded by a lock; /api/state returns a
  consistent snapshot. Same seed => same results as the Streamlit app.
- Add pytest tests for: reset determinism, step advances tick, state shape, decision
  approve/reject transitions, 404/409 errors.
- Verify with curl and show me real JSON from a 20-tick run.

PHASE 2 - Frontend shell (static, mock data)
- Scaffold /web. Recreate the reference page pixel-close: rail, topbar, intro + KPIs,
  decision list, review panel, stats column. Use the mock data from reference/app.js
  behind a typed data layer (src/api/client.ts) so swapping in the real API is one change.
- Build the map exactly as DESIGN_SPEC section 5 says (rotated divs, NOT Plotly/SVG):
  a <RoadMap/> component that takes nodes, roads, routes, vehicles as props.
- Components (suggested): AppShell, Rail, Topbar, KpiCard, DecisionCard, DecisionList,
  RoadMap, ExplanationPanel, KeyFactors, RiskStrip, ActionBar, OversightCard,
  ImpactCard, ActivityList, ControlBar.
- Compare against the reference screenshot at 1440px and at ~800px and fix differences.

PHASE 3 - Wire to the backend
- Replace mock data with the real API. Poll /api/state every 1000 ms while running
  (use an AbortController, no overlapping requests, stop when paused/finished).
- Add the live-simulation parts from DESIGN_SPEC section 6: control bar (Start, Pause,
  Reset, progress "Tick n / max"), vehicle markers interpolated along their road,
  status pill colours, and the empty/ready state with a clear Start call-to-action.
- Update only what changed each tick (roads colours/thickness, route layers, vehicles,
  KPIs). Never rebuild nodes/labels per tick.
- Sidebar replacement: a "Simulation setup" drawer or page with Topology, Scenario,
  Strategy (visible) and Vehicles, Duration, Arrival interval, Seed (under "Advanced"),
  each with a help tooltip and an "Apply & reset" button.
- Wire Approve / Reject / Modify to the decision endpoints; approving must actually
  change the vehicle's route in the simulation.

PHASE 4 - Remaining pages, polish, QA
- Build Live Simulation, Vehicles, Coordination, Analytics, About as real pages (react-
  router) using the same components and tokens. Reuse the existing Streamlit analytics
  charts' data; draw charts with a light-theme library (Recharts) in the same style.
- Accessibility pass from DESIGN_SPEC section 7. Keyboard-only walkthrough.
- Run the app end to end: configure -> start -> ticks -> approve a decision -> reset.
  Check the browser console and the server log for errors.
- Write a README: how to install and run backend + frontend, and a short architecture note.

DECISIONS (follow unless I say otherwise)
- If the simulation does not produce "review decisions", implement them in
  api/decisions.py as described at the bottom of api-contract.md (Dijkstra on congestion-
  weighted edges, threshold, templated explanation). Everything shown in the UI must be
  derived from real simulation numbers. Do not hard-code or invent statistics in the
  frontend. Sample values from the reference must not ship.
- Do not add dependencies without listing them first. Prefer what is already installed.
- Do not change simulation behaviour or seeds. If you think the simulation has a bug,
  tell me instead of fixing it.
- Keep every change small and reviewable. Commit after each phase with a clear message.

DEFINITION OF DONE
- `uvicorn api.main:app` + `npm run dev` gives a dashboard that matches the reference
  look, runs the real simulation live, and lets me approve/reject re-routes.
- Same seed produces the same KPIs as the old Streamlit app.
- No console errors, keyboard accessible, readable at 800px and 1440px.
- At the end, give me a summary: files created/changed, how to run, and anything you
  were unsure about.
```

---

## If Antigravity struggles

- **Look is off:** tell it "match handoff/reference/index.html exactly, compare screenshots at 1440px, and list each visual difference before fixing".
- **Too heavy:** "reduce shadow intensity by 30%" (edit `--shadow-card` and `.key` shadows).
- **Map wrong:** "the map must follow DESIGN_SPEC section 5: rotated divs, one drop-shadow filter on the roads wrapper."
- **Backend slow or flickering:** "poll with AbortController, update only changed state, no full re-render per tick."
- **Stuck on the sim code:** paste your simulation's main file and `app.py` into the chat and say "map these to api-contract.md".
