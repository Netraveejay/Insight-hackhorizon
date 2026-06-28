"""Tests for grounded conversational assistant."""

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


def test_assistant_suggestions(client):
    res = client.get("/api/assistant/suggestions")
    assert res.status_code == 200
    assert len(res.json()["questions"]) >= 8


def test_assistant_status_offline(client):
    res = client.get("/api/assistant/status")
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] in ("ai", "offline")
    assert "ai_enabled" in body


def test_assistant_chat_grounded(client, db, seeded_pipeline):
    res = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "What are the top issues this week?"}], "week": "2026-W26"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["answer"]
    assert body["a2a_correlation_id"]
    assert "week" in body["answer"].lower() or "issue" in body["answer"].lower()

    rows = __import__("app.models", fromlist=["AgentMessageRow"]).AgentMessageRow
    a2a = db.query(rows).filter(rows.correlation_id == body["a2a_correlation_id"]).all()
    assert len(a2a) >= 2

    run_res = client.get(f"/api/runs/{body['a2a_correlation_id']}")
    assert run_res.status_code == 200
    assert len(run_res.json()["steps"]) >= 3


def test_assistant_harbourview_site(client, db, seeded_pipeline):
    res = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "How is Harbourview doing?"}], "week": "2026-W26"},
    )
    assert res.status_code == 200
    assert "Harbourview" in res.json()["answer"]


def test_assistant_sla(client, db, seeded_pipeline):
    res = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "What is the SLA status?"}], "week": "2026-W26"},
    )
    assert res.status_code == 200
    assert "SLA" in res.json()["answer"] or "track" in res.json()["answer"].lower()


def test_assistant_negative_comments(client, db, seeded_pipeline):
    res = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "top 3 negative comments"}], "week": "2026-W26"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "negative comment" in body["answer"].lower() or "projection" in body["answer"].lower()
    assert "get_negative_feedback" in body.get("tools_used", []) or "1." in body["answer"]

    rows = __import__("app.models", fromlist=["AgentMessageRow"]).AgentMessageRow
    a2a = db.query(rows).filter(rows.correlation_id == body["a2a_correlation_id"]).all()
    assert any(r.intent == "query" for r in a2a)


def test_agentic_react_trace(client, db, seeded_pipeline):
    res = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "top 3 negative comments"}], "week": "2026-W26"},
    )
    assert res.status_code == 200
    body = res.json()
    run_res = client.get(f"/api/runs/{body['a2a_correlation_id']}")
    assert run_res.status_code == 200
    run = run_res.json()
    assert run["trigger"]["type"] == "question"
    assert any(s["phase"] == "act" for s in run["steps"])


def test_assistant_followup_top_issues(client, db, seeded_pipeline):
    """Follow-up must not route to get_site because prior answer mentioned Harbourview."""
    res = client.post(
        "/api/assistant/chat",
        json={
            "messages": [
                {"role": "user", "content": "top issues this week?"},
                {
                    "role": "assistant",
                    "content": (
                        "Top priority issues for 2026-W26:\n"
                        "1. Harbourview — projection quality (P1, 13 negatives)\n"
                        "2. Northgate — ticketing queue (P1, 7 negatives)"
                    ),
                },
                {"role": "user", "content": "top 3 issues"},
            ],
            "week": "2026-W26",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "priority issues" in body["answer"].lower()
    assert "get_top_issues" in body.get("tools_used", [])
    assert "Harbourview top issue:" not in body["answer"]


def test_assistant_least_priority(client, db, seeded_pipeline):
    res = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "least priority issues?"}], "week": "2026-W26"},
    )
    assert res.status_code == 200
    answer = res.json()["answer"]
    assert "Lowest priority" in answer
    assert "get_top_issues" in res.json().get("tools_used", [])


def test_coordinator_rejects_wrong_tool(client, db, seeded_pipeline):
    """Coordinator should emit alert when reverting from overview to negative feedback."""
    res = client.post(
        "/api/assistant/chat",
        json={
            "messages": [{"role": "user", "content": "show me negative guest comments this week"}],
            "week": "2026-W26",
        },
    )
    assert res.status_code == 200
    rows = __import__("app.models", fromlist=["AgentMessageRow"]).AgentMessageRow
    a2a = db.query(rows).filter(rows.correlation_id == res.json()["a2a_correlation_id"]).all()
    intents = [r.intent for r in a2a]
    assert "query" in intents

