"""Pydantic schemas aligned with handoff/api-contract.md."""
from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


SimStatusLiteral = Literal["ready", "running", "paused", "finished"]
RoadLevelLiteral = Literal["idle", "low", "moderate", "high", "severe"]
VehicleStateLiteral = Literal["moving", "queued"]
DecisionPriorityLiteral = Literal["high", "medium", "low"]
DecisionStatusLiteral = Literal["pending", "approved", "rejected", "modified"]
ActivityVerbLiteral = Literal["Approved", "Modified", "Rejected"]


class ConfigureRequest(BaseModel):
    topology: str = "Metro Smart City (12 Nodes)"
    scenario: str = "Normal Traffic"
    strategy: str = "Independent"
    vehicles: int = Field(default=60, ge=5, le=500)
    durationTicks: int = Field(default=200, ge=20, le=1000)
    arrivalInterval: int = Field(default=1, ge=0, le=20)
    seed: int = Field(default=42, ge=0, le=999999)


class StepRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=50)


class ModifyDecisionRequest(BaseModel):
    note: str = ""
    route: Optional[List[str]] = None


class KPIsSchema(BaseModel):
    totalVehicles: int
    activeVehicles: int
    queuedAtIntersections: int
    completedJourneys: int
    completionRatePct: float
    avgTravelTimeSec: float
    avgDelaySec: float
    networkCongestionPct: float
    occupiedSlots: int
    totalSlots: int


class NodeSchema(BaseModel):
    id: str
    label: str
    x: float
    y: float
    labelAt: Optional[str] = None


class RoadSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_node: str = Field(alias="from")
    to: str
    level: RoadLevelLiteral
    occupancyPct: float
    vehicles: int
    capacity: int
    lanes: int
    speedKmh: float
    toll: float
    queue: int


class CongestionDistributionSchema(BaseModel):
    idle: int
    low: int
    moderate: int
    high: int
    severe: int


class VehicleMarkerSchema(BaseModel):
    id: str
    road: str
    progress: float
    state: VehicleStateLiteral
    fromNode: str
    toNode: str
    speedKmh: float
    behaviour: str
    delaySec: float


class SimStateResponse(BaseModel):
    status: SimStatusLiteral
    tick: int
    maxTicks: int
    scenario: str
    strategy: str
    topology: str
    seed: int
    arrivalInterval: int
    kpis: KPIsSchema
    nodes: List[NodeSchema]
    roads: List[RoadSchema]
    congestionDistribution: CongestionDistributionSchema
    vehicles: List[VehicleMarkerSchema]


class FactorSchema(BaseModel):
    label: str
    valuePct: int


class RiskSchema(BaseModel):
    title: str
    detail: str


class ImpactSchema(BaseModel):
    travelTimeSec: float
    queueVehicles: int
    energyKwh: float


class DecisionSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    vehicleId: str
    priority: DecisionPriorityLiteral
    status: DecisionStatusLiteral
    confidence: int
    tick: int
    from_node: str = Field(alias="from")
    to: str
    tags: List[str]
    currentRoute: List[str]
    suggestedRoute: List[str]
    estTravelSec: float
    delaySavedSec: float
    explanation: str
    bullets: List[str]
    factors: List[FactorSchema]
    risks: List[RiskSchema]
    impact: ImpactSchema
    historicalSuccessPct: int
    operatorNote: Optional[str] = None


class DecisionCountsSchema(BaseModel):
    pending: int
    approved: int
    history: int
    lowConfidence: int


class DecisionListResponse(BaseModel):
    counts: DecisionCountsSchema
    items: List[DecisionSchema]


class OversightWeekSchema(BaseModel):
    totalDecisions: int
    delaySavedSec: float
    queueReductionPct: float
    energySavedKwh: float


class OversightResponse(BaseModel):
    approvedPct: int
    modifiedPct: int
    rejectedPct: int
    week: OversightWeekSchema


class ActivityItemSchema(BaseModel):
    id: str
    verb: ActivityVerbLiteral
    from_node: str = Field(alias="from")
    to: str
    at: str
    vehicleId: Optional[str] = None
    tick: Optional[int] = None

    model_config = ConfigDict(populate_by_name=True)


class FleetVehicleSchema(BaseModel):
    id: str
    origin: str
    destination: str
    currentNode: str
    targetNode: Optional[str]
    road: Optional[str]
    route: List[str]
    behaviour: str
    status: str
    speedKmh: float
    travelTimeSec: float
    waitingTimeSec: float
    delaySec: float
    tollPaid: float
    reroutes: int
    scheduledTick: int


class TelemetryPointSchema(BaseModel):
    tick: int
    activeVehicles: int
    completedVehicles: int
    queuedVehicles: int
    avgSpeedKmh: float
    avgDensityPct: float
    totalSystemDelay: float
