"""Shared pytest configuration — isolated DB and API client."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Configure test environment before any app.db import (pytest loads conftest first).
_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_INSIGHT_ROOT = _BACKEND_DIR.parent
_TEST_DB = _TESTS_DIR / ".pytest_insight.db"

if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["AUTO_SEED"] = "false"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ.setdefault("AUTH_SECRET", "test-secret")
os.environ.setdefault("RULES_PATH", str(_INSIGHT_ROOT / "rules" / "rules.v1.yaml"))
os.environ.setdefault("REPORTS_DIR", str(_TESTS_DIR / "reports_out"))

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session")
def rules():
    from app.rules import load_rules

    return load_rules()


@pytest.fixture(scope="session")
def init_test_db():
    from app.db import init_db

    init_db()
    yield
    if _TEST_DB.exists():
        _TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def db(init_test_db):
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(init_test_db):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_headers(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "insight2026"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clean_artifact_tables(db):
    """Prevent cross-test DB pollution in the isolated test database."""
    from app.models import (
        AgentMessageRow,
        AgentRunRow,
        AlertRow,
        AuditRecordRow,
        ClusterRow,
        DetectionRow,
        DistributionLogRow,
        FeedbackRaw,
        FeedbackScored,
        FeedbackTranslated,
        GeneratedReportRow,
        InsightRow,
        LanguageStatsRow,
        ReasoningStepRow,
        RunRow,
        SourceCoverageRow,
        TriggerRow,
    )

    for model in (
        ReasoningStepRow,
        AgentRunRow,
        TriggerRow,
        AgentMessageRow,
        AlertRow,
        AuditRecordRow,
        ClusterRow,
        DetectionRow,
        DistributionLogRow,
        FeedbackRaw,
        FeedbackScored,
        FeedbackTranslated,
        GeneratedReportRow,
        InsightRow,
        LanguageStatsRow,
        SourceCoverageRow,
        RunRow,
    ):
        db.query(model).delete()
    db.commit()
    db.expunge_all()
    yield
    db.expunge_all()
