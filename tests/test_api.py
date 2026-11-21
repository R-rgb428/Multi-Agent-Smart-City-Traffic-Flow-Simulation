"""Tests for the FastAPI wrapper around the Smart City Traffic Simulation."""
from __future__ import annotations
import time
from fastapi.testclient import TestClient

from api.main import app, manager


client = TestClient(app)


def _setup_congested_rush_hour(vehicles: int = 90) -> dict:
    res = client.post(
        "/api/sim/configure",
        json={
            "topology": "Metro Smart City (12 Nodes)",
            "scenario": "Rush Hour",
            "strategy": "Independent",
            "vehicles": vehicles,
            "durationTicks": 250,
            "arrivalInterval": 1,
            "seed": 42,
        },
    )
    assert res.status_code == 200
    # Step until at least one pending decision appears (rush hour builds peak bursts quickly)
    for _ in range(35):
        step_res = client.post("/api/sim/step", json={"ticks": 2})
        assert step_res.status_code == 200
        dec_res = client.get("/api/decisions?status=pending")
        assert dec_res.status_code == 200
        if dec_res.json()["counts"]["pending"] > 0:
            return dec_res.json()
    raise AssertionError("Expected at least one AI decision during congested rush-hour simulation.")


def test_configure_and_state_contract():
    res = client.post(
        "/api/sim/configure",
        json={
            "topology": "Metro Smart City (12 Nodes)",
            "scenario": "Normal Traffic",
            "strategy": "Independent",
            "vehicles": 100,
            "durationTicks": 300,
            "arrivalInterval": 1,
            "seed": 42,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["tick"] == 0
    assert data["maxTicks"] == 300
    assert data["kpis"]["totalVehicles"] == 100
    assert data["kpis"]["totalSlots"] == 516
    assert len(data["nodes"]) == 12
    assert len(data["roads"]) == 38
    assert sum(data["congestionDistribution"].values()) == 38

    # Check coordinates sit cleanly within 640x340 design space and aliases render as "from"
    for node in data["nodes"]:
        assert 0 <= node["x"] <= 640
        assert 0 <= node["y"] <= 340
    for road in data["roads"]:
        assert "from" in road and "to" in road
        assert road["id"] == f"{road['from']}>{road['to']}"


def test_step_start_pause_reset_lifecycle():
    client.post(
        "/api/sim/configure",
        json={
            "topology": "Metro Smart City (12 Nodes)",
            "scenario": "Normal Traffic",
            "strategy": "Independent",
            "vehicles": 60,
            "durationTicks": 200,
            "arrivalInterval": 1,
            "seed": 42,
        },
    )

    stepped = client.post("/api/sim/step", json={"ticks": 5})
    assert stepped.status_code == 200
    assert stepped.json()["tick"] == 5
    assert stepped.json()["status"] == "paused"

    started = client.post("/api/sim/start")
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    time.sleep(0.55)
    paused = client.post("/api/sim/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    assert paused.json()["tick"] >= 5

    reset = client.post("/api/sim/reset")
    assert reset.status_code == 200
    assert reset.json()["status"] == "ready"
    assert reset.json()["tick"] == 0


def test_decisions_approve_reject_modify_mutate_sim_and_oversight():
    decisions_data = _setup_congested_rush_hour(vehicles=100)
    pending_items = decisions_data["items"]
    assert len(pending_items) >= 1

    # 1. Approve first pending decision and verify vehicle route updates in engine
    first = pending_items[0]
    assert first["delaySavedSec"] > 5.0
    assert sum(f["valuePct"] for f in first["factors"]) == 100
    veh_before = manager.engine.fleet_manager.vehicles[first["vehicleId"]]
    reroutes_before = veh_before.reroute_count

    app_res = client.post(f"/api/decisions/{first['id']}/approve")
    assert app_res.status_code == 200
    app_json = app_res.json()
    assert app_json["status"] == "approved"
    assert veh_before.reroute_count == reroutes_before + 1

    # Double approve -> 409 conflict with {"error": ...}
    dup_res = client.post(f"/api/decisions/{first['id']}/approve")
    assert dup_res.status_code == 409
    assert "error" in dup_res.json()

    # 2. If another decision exists, reject it cleanly; otherwise step more to get one
    pending2 = client.get("/api/decisions?status=pending").json()["items"]
    if not pending2:
        client.post("/api/sim/step", json={"ticks": 6})
        pending2 = client.get("/api/decisions?status=pending").json()["items"]

    assert len(pending2) >= 1
    second = pending2[0]
    rej_res = client.post(f"/api/decisions/{second['id']}/reject")
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"

    # 3. Modify with note (keeping route) or custom valid route
    pending3 = client.get("/api/decisions?status=pending").json()["items"]
    if not pending3:
        client.post("/api/sim/step", json={"ticks": 6})
        pending3 = client.get("/api/decisions?status=pending").json()["items"]

    if pending3:
        third = pending3[0]
        mod_res = client.post(
            f"/api/decisions/{third['id']}/modify",
            json={"note": "Hold arterial cadence", "route": third["suggestedRoute"]},
        )
        assert mod_res.status_code == 200
        assert mod_res.json()["status"] == "modified"
        assert mod_res.json()["operatorNote"] == "Hold arterial cadence"

    # 4. Check oversight and activity endpoints
    ov_res = client.get("/api/oversight")
    assert ov_res.status_code == 200
    ov = ov_res.json()
    assert ov["approvedPct"] + ov["modifiedPct"] + ov["rejectedPct"] == 100
    assert ov["week"]["delaySavedSec"] > 0
    assert ov["week"]["energySavedKwh"] > 0

    act_res = client.get("/api/activity?limit=5")
    assert act_res.status_code == 200
    acts = act_res.json()
    assert len(acts) >= 2
    assert "from" in acts[0] and "to" in acts[0]
    assert acts[0]["verb"] in ("Approved", "Modified", "Rejected")


def test_error_responses_match_contract():
    unknown = client.get("/api/decisions/R-99999")
    assert unknown.status_code == 404
    assert "error" in unknown.json()

    bad_cfg = client.post("/api/sim/configure", json={"scenario": "Nonexistent Scenario"})
    assert bad_cfg.status_code == 400
    assert "error" in bad_cfg.json()

    bad_filter = client.get("/api/decisions?status=invalid")
    assert bad_filter.status_code == 400
    assert "error" in bad_filter.json()
