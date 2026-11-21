# API contract (frontend <-> Python simulation backend)

The frontend only needs JSON. Wrap the existing Python simulation with **FastAPI**. Do not rewrite the simulation logic - import it and call it.

All ids are strings. Times are ticks (integers) unless stated. Percentages are 0-100.

## Simulation control

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/sim/configure` | `{ topology, scenario, strategy, vehicles, durationTicks, arrivalInterval, seed }` | `State` (reset, status `ready`) |
| POST | `/api/sim/start` | - | `State` |
| POST | `/api/sim/pause` | - | `State` |
| POST | `/api/sim/reset` | - | `State` |
| POST | `/api/sim/step` | `{ ticks?: 1 }` | `State` |
| GET  | `/api/state` | - | `State` |

```jsonc
// State
{
  "status": "ready | running | paused | finished",
  "tick": 5, "maxTicks": 300,
  "scenario": "Normal Traffic", "strategy": "Independent", "topology": "Metro Smart City (12 Nodes)", "seed": 42,
  "kpis": {
    "totalVehicles": 100, "activeVehicles": 6, "queuedAtIntersections": 0,
    "completedJourneys": 0, "completionRatePct": 0.0,
    "avgTravelTimeSec": 0.0, "avgDelaySec": 0.0,
    "networkCongestionPct": 1.2, "occupiedSlots": 6, "totalSlots": 516
  },
  "nodes": [ { "id": "N_GATE", "x": 320, "y": 40 } ],            // design space 640 x 340
  "roads": [
    { "id": "W_BYPASS>NW_RES", "from": "W_BYPASS", "to": "NW_RES",
      "level": "idle | low | moderate | high | severe", "occupancyPct": 12.5, "vehicles": 3, "capacity": 24 }
  ],
  "congestionDistribution": { "idle": 34, "low": 4, "moderate": 0, "high": 0, "severe": 0 },
  "vehicles": [
    { "id": "V-007", "road": "W_BYPASS>NW_RES", "progress": 0.42, "state": "moving | queued" }
  ]
}
```

`nodes[].x/y` come from the backend so the layout is not hard-coded in the UI. If the simulation has no coordinates, copy the table from `reference/app.js` (`NODES`) into the backend.

## Review decisions (the "AI Review Center" feature)

| Method | Path | Returns |
|---|---|---|
| GET  | `/api/decisions?status=pending\|approved\|history` | `{ counts: {pending, approved, history, lowConfidence}, items: Decision[] }` |
| GET  | `/api/decisions/{id}` | `Decision` |
| POST | `/api/decisions/{id}/approve` | `Decision` |
| POST | `/api/decisions/{id}/reject` | `Decision` |
| POST | `/api/decisions/{id}/modify` | body `{ note: string, route?: string[] }` -> `Decision` |
| GET  | `/api/oversight` | `{ approvedPct, modifiedPct, rejectedPct, week: { totalDecisions, delaySavedSec, queueReductionPct, energySavedKwh } }` |
| GET  | `/api/activity?limit=5` | `[ { id, verb: "Approved|Modified|Rejected", from, to, at } ]` |

```jsonc
// Decision
{
  "id": "R-1045", "vehicleId": "V-007",
  "priority": "high | medium | low",
  "status": "pending | approved | rejected | modified",
  "confidence": 87, "tick": 42,
  "from": "NW_RES", "to": "SE_SUB",
  "tags": ["Congestion risk", "Signal delay"],
  "currentRoute":   ["NW_RES", "W_IND", "SW_PORT", "S_CIVIC", "SE_SUB"],
  "suggestedRoute": ["NW_RES", "DOWNTOWN", "E_FIN", "SE_SUB"],
  "estTravelSec": 46, "delaySavedSec": 38,
  "explanation": "One short paragraph.",
  "bullets": ["Avoids 2 roads at high density", "..."],
  "factors": [ { "label": "Traffic density", "valuePct": 92 } ],
  "risks":   [ { "title": "Density rising on W_IND to SW_PORT", "detail": "Expected within 12 ticks" } ],
  "impact":  { "travelTimeSec": -38, "queueVehicles": -3, "energyKwh": -0.4 },
  "historicalSuccessPct": 94
}
```

### If the simulation does not already produce decisions

Generate them in a small module (`decisions.py`), do not fake them in the frontend:

1. Every N ticks, for each vehicle that has not reached its destination, compute its current route's cost and an alternative route's cost using **Dijkstra** with edge weight `free_flow_time * (1 + k * occupancy^2)`.
2. If the alternative saves more than a threshold (e.g. 5 s), emit a Decision.
3. `confidence` = how reliable the estimate is: saving relative to cost, shrunk when occupancy data is sparse. `priority` from `delaySavedSec` and the congestion level of the avoided roads.
4. `factors` = normalised contributions (density, signal/intersection wait, capacity, queue length). `bullets` and `explanation` are templated text built from the same numbers (never invented).
5. Approve -> apply the new route to the vehicle in the sim. Reject -> keep the route. Modify -> apply the operator's route if given, else keep and store the note.
6. `historicalSuccessPct` = fraction of earlier approved decisions of the same kind whose realised saving was positive (store outcomes as the sim runs).

## Errors

JSON `{ "error": "message" }` with the right HTTP status (400 bad input, 404 unknown id, 409 wrong state e.g. approving twice). CORS: allow the Vite dev origin (`http://localhost:5173`).
