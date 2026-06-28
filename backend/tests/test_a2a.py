"""Tests for A2A message bus and agent registry."""

import pytest

from app.models import AgentMessageRow


def test_agent_registry(client):
    res = client.get("/api/agents")
    assert res.status_code == 200
    data = res.json()
    assert len(data["agents"]) >= 12
    ids = {a["id"] for a in data["agents"]}
    assert "assistant" in ids
    assert "coordinator" in ids
    assert "ingestion" in ids


@pytest.mark.integration
def test_pipeline_emits_a2a_messages(db):
    from unittest.mock import patch

    from app.orchestrator import Orchestrator
    from tests.helpers import raw_feedback
    from tests.test_orchestrator import _ListConnector

    raw_items = [raw_feedback(text="Queue very long at peak")]
    with patch("app.orchestrator.load_connectors", return_value=[_ListConnector(raw_items)]):
        result = Orchestrator(db).run_pipeline(week="2026-W26", cadence="test")

    rows = db.query(AgentMessageRow).filter(AgentMessageRow.correlation_id == result.run_id).all()
    assert len(rows) >= 10
    intents = {r.intent for r in rows}
    assert "handoff" in intents
    assert "status" in intents


def test_a2a_messages_endpoint(client, db):
    from unittest.mock import patch

    from app.orchestrator import Orchestrator
    from tests.helpers import raw_feedback
    from tests.test_orchestrator import _ListConnector

    raw_items = [raw_feedback(text="Screen dim")]
    with patch("app.orchestrator.load_connectors", return_value=[_ListConnector(raw_items)]):
        result = Orchestrator(db).run_pipeline(week="2026-W26", cadence="test")

    res = client.get(f"/api/a2a/messages?correlation_id={result.run_id}")
    assert res.status_code == 200
    assert len(res.json()["messages"]) >= 5
