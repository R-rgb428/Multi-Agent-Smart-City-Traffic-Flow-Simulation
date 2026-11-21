"""FastAPI entrypoint wrapping the Smart City Traffic Flow Simulation."""
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.decisions import ApiError
from api.manager import SimulationManager
from api.schemas import (
    ActivityItemSchema,
    ConfigureRequest,
    DecisionListResponse,
    DecisionSchema,
    FleetVehicleSchema,
    ModifyDecisionRequest,
    OversightResponse,
    SimStateResponse,
    StepRequest,
    TelemetryPointSchema,
)

manager = SimulationManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    manager.shutdown()


app = FastAPI(
    title="Smart City Traffic Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    msg = "; ".join(err.get("msg", "Invalid input") for err in exc.errors()) or "Invalid request payload."
    return JSONResponse(status_code=400, content={"error": msg})


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/sim/configure", response_model=SimStateResponse)
def configure_sim(req: ConfigureRequest):
    return manager.configure(
        topology=req.topology,
        scenario=req.scenario,
        strategy=req.strategy,
        vehicles=req.vehicles,
        duration_ticks=req.durationTicks,
        arrival_interval=req.arrivalInterval,
        seed=req.seed,
    )


@app.post("/api/sim/start", response_model=SimStateResponse)
def start_sim():
    return manager.start()


@app.post("/api/sim/pause", response_model=SimStateResponse)
def pause_sim():
    return manager.pause()


@app.post("/api/sim/reset", response_model=SimStateResponse)
def reset_sim():
    return manager.reset()


@app.post("/api/sim/step", response_model=SimStateResponse)
def step_sim(req: Optional[StepRequest] = None):
    ticks = req.ticks if req else 1
    return manager.step(ticks=ticks)


@app.get("/api/state", response_model=SimStateResponse)
def get_state():
    return manager.get_state()


@app.get("/api/decisions", response_model=DecisionListResponse)
def list_decisions(status: Optional[str] = Query(default=None)):
    if status is not None and status not in ("pending", "approved", "history"):
        raise ApiError(400, f"Invalid status filter '{status}'. Use pending, approved, or history.")
    return manager.list_decisions(status_filter=status)


@app.get("/api/decisions/{decision_id}", response_model=DecisionSchema)
def get_decision(decision_id: str):
    return manager.get_decision(decision_id)


@app.post("/api/decisions/{decision_id}/approve", response_model=DecisionSchema)
def approve_decision(decision_id: str):
    return manager.approve_decision(decision_id)


@app.post("/api/decisions/{decision_id}/reject", response_model=DecisionSchema)
def reject_decision(decision_id: str):
    return manager.reject_decision(decision_id)


@app.post("/api/decisions/{decision_id}/modify", response_model=DecisionSchema)
def modify_decision(decision_id: str, req: ModifyDecisionRequest):
    return manager.modify_decision(decision_id, note=req.note, route=req.route)


@app.get("/api/oversight", response_model=OversightResponse)
def get_oversight():
    return manager.get_oversight()


@app.get("/api/activity", response_model=List[ActivityItemSchema])
def get_activity(limit: int = Query(default=5, ge=1, le=40)):
    return manager.get_activity(limit=limit)


@app.get("/api/vehicles", response_model=List[FleetVehicleSchema])
def get_vehicles():
    return manager.get_fleet_vehicles()


@app.get("/api/telemetry", response_model=List[TelemetryPointSchema])
def get_telemetry():
    return manager.get_telemetry()
