"""End-to-end API tests — HTTP layer with TestClient."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.helpers import raw_feedback
from tests.test_orchestrator import _ListConnector, WEEK_TS


@pytest.fixture
def pipeline_run(db):
    """Run pipeline once for API tests that need populated data."""
    from app.orchestrator import Orchestrator

    raw_items = []
    for week, n in {"2026-W24": 4, "2026-W25": 6, "2026-W26": 8}.items():
        for i in range(n):
            raw_items.append(
                raw_feedback(
                    week=week,
                    ts=WEEK_TS[week],
                    text=f"Screen dim and out of focus {week} #{i}",
                )
            )
        if week in ("2026-W25", "2026-W26"):
            raw_items.append(
                raw_feedback(
                    source_type="staff",
                    channel="kpi_email",
                    week=week,
                    ts=WEEK_TS[week],
                    text=f"KPI: projector lamp below brightness threshold ({week})",
                )
            )

    with patch("app.orchestrator.load_connectors", return_value=[_ListConnector(raw_items)]):
        result = Orchestrator(db).run_pipeline(week="2026-W26", cadence="e2e")
    return result.model_dump()


@pytest.mark.e2e
class TestHealth:
    def test_health_endpoint(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


@pytest.mark.e2e
class TestAuthFlow:
    def test_login_and_me(self, client):
        res = client.post("/api/auth/login", json={"username": "admin", "password": "insight2026"})
        assert res.status_code == 200
        token = res.json()["token"]
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["role"] == "admin"

    def test_protected_reports_requires_auth(self, client):
        res = client.get("/api/reports?week=2026-W26")
        assert res.status_code == 401


@pytest.mark.e2e
class TestPipelineAPI:
    def test_run_pipeline_via_http(self, client, db):
        raw_items = [
            raw_feedback(text=f"Dim screen HTTP test {i}") for i in range(5)
        ]
        with patch("app.orchestrator.load_connectors", return_value=[_ListConnector(raw_items)]):
            res = client.post("/api/pipeline/run?week=2026-W26")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["run_id"]
        assert body["items_scored"] > 0

    def test_run_pipeline_returns_steps(self, pipeline_run):
        assert pipeline_run["run_id"]
        assert pipeline_run["week"] == "2026-W26"
        assert len(pipeline_run["steps"]) >= 7
        step_ids = {s["id"] for s in pipeline_run["steps"]}
        assert "ingest" in step_ids
        assert "detect" in step_ids
        assert "explain" in step_ids

    def test_explain_after_run(self, client, pipeline_run):
        res = client.get("/api/pipeline/explain?week=2026-W26")
        assert res.status_code == 200
        body = res.json()
        assert body["run_id"] == pipeline_run["run_id"]
        assert body["explanation"]["headline"]


@pytest.mark.e2e
class TestIssuesAndOverviewAPI:
    def test_issues_include_root_cause_and_sla(self, client, admin_headers, pipeline_run):
        res = client.get("/api/issues?week=2026-W26", headers=admin_headers)
        assert res.status_code == 200
        issues = res.json()["issues"]
        assert len(issues) > 0
        p1 = next((i for i in issues if i["priority"] == "P1"), issues[0])
        assert p1.get("root_cause_summary")
        assert p1.get("sla_status") in ("on_track", "at_risk", "breached")

    def test_issue_detail_has_root_cause_block(self, client, admin_headers, pipeline_run):
        issues = client.get("/api/issues?week=2026-W26", headers=admin_headers).json()["issues"]
        cluster_id = issues[0]["cluster_id"]
        res = client.get(f"/api/issues/{cluster_id}", headers=admin_headers)
        assert res.status_code == 200
        detail = res.json()
        assert detail["root_cause"] is not None
        assert detail["root_cause"]["summary"]
        assert detail["sla"] is not None
        assert detail["sla"]["label"]

    def test_overview_sla_summary(self, client, admin_headers, pipeline_run):
        res = client.get("/api/overview?week=2026-W26", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["week"] == "2026-W26"
        assert "sla_summary" in data
        if data["open_issues"] > 0:
            total = (
                data["sla_summary"]["on_track"]
                + data["sla_summary"]["at_risk"]
                + data["sla_summary"]["breached"]
            )
            assert total >= 1

    def test_feed_has_pipeline_funnel(self, client, admin_headers, pipeline_run):
        res = client.get("/api/feed?week=2026-W26", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["has_data"] is True
        assert data["pipeline"]["total_received"] > 0


@pytest.mark.e2e
class TestAlertsAPI:
    def test_alerts_include_sla_fields(self, client, admin_headers, pipeline_run):
        res = client.get("/api/alerts?week=2026-W26", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["week"] == "2026-W26"
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "sla_status" in alert or alert.get("priority")
