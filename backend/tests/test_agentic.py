"""Tests for agentic ReAct loop and investigator."""

import pytest


@pytest.fixture
def seeded_pipeline(db):
    from unittest.mock import patch

    from app.orchestrator import Orchestrator
    from tests.helpers import raw_feedback
    from tests.test_orchestrator import _ListConnector

    raw_items = [raw_feedback(text=f"Projection dim #{i}") for i in range(8)]
    raw_items.append(
        raw_feedback(source_type="staff", channel="kpi_email", text="KPI: lamp fault")
    )
    with patch("app.orchestrator.load_connectors", return_value=[_ListConnector(raw_items)]):
        Orchestrator(db).run_pipeline(week="2026-W26", cadence="test")


def test_deterministic_loop_investigator(client, db, seeded_pipeline):
    from app.models import ClusterRow

    cluster = db.query(ClusterRow).first()
    assert cluster
    res = client.post(
        "/api/runs/investigate",
        json={"cluster_id": cluster.cluster_id, "week": cluster.week},
    )
    assert res.status_code == 200
    body = res.json()
    run = body["run"]
    assert run["runner"] == "investigator"
    assert run["trigger"]["type"] == "manual"
    assert len(run["steps"]) >= 4
    phases = [s["phase"] for s in run["steps"]]
    assert "think" in phases
    assert "act" in phases
    assert "observe" in phases
    assert run["outcome"]
    assert "P1" in run["outcome"] or "Briefing" in run["outcome"] or "What" in run["outcome"]


def test_conversational_react_run(client, db, seeded_pipeline):
    res = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "top 3 negative comments"}], "week": "2026-W26"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["answer"]
    assert body.get("agentic_rounds", 0) >= 1

    run_res = client.get(f"/api/runs/{body['a2a_correlation_id']}")
    assert run_res.status_code == 200
    run = run_res.json()
    assert run["runner"] == "conversational"
    assert run["trigger"]["type"] == "question"
    assert any(s["phase"] == "act" for s in run["steps"])


def test_list_runs(client, db, seeded_pipeline):
    client.post(
        "/api/runs/investigate",
        json={"cluster_id": db.query(__import__("app.models", fromlist=["ClusterRow"]).ClusterRow).first().cluster_id},
    )
    res = client.get("/api/runs")
    assert res.status_code == 200
    assert len(res.json()["runs"]) >= 1


def test_check_contagion_tool(db, seeded_pipeline):
    from app.agentic.tools import check_contagion

    result = check_contagion(db, "projection_quality", "2026-W26")
    assert "site_count" in result
    assert "spreading" in result
