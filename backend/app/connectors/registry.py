from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.connectors.base import FeedbackConnector
from app.connectors.file import FileConnector
from app.connectors.graph_stub import GraphDisruptionConnector, GraphInboxConnector, GraphKPIConnector
from app.connectors.seed import SeedConnector


def load_connectors() -> list[FeedbackConnector]:
    """Active connectors for pipeline ingestion."""
    settings = get_settings()
    connectors: list[FeedbackConnector] = []

    if settings.feedback_file_path:
        path = Path(settings.feedback_file_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists():
            connectors.append(FileConnector(path))

    if not connectors:
        connectors.append(SeedConnector())

    return connectors


def connector_catalog() -> list[dict]:
    """All connectors and whether they are active / production-ready."""
    settings = get_settings()
    active = {c.name for c in load_connectors()}
    file_path = settings.feedback_file_path
    resolved_file = None
    if file_path:
        p = Path(file_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        resolved_file = str(p)

    return [
        {
            "id": "file",
            "label": "Feedback file import",
            "status": "active" if "file" in active else "available",
            "production_ready": True,
            "description": "Point FEEDBACK_FILE_PATH at a JSON export of real guest/staff feedback.",
            "config": "FEEDBACK_FILE_PATH",
            "configured": bool(resolved_file and Path(resolved_file).exists()),
            "path": resolved_file,
        },
        {
            "id": "seed",
            "label": "Synthetic seed data",
            "status": "active" if "seed" in active else "standby",
            "production_ready": False,
            "description": "Demo dataset with planted Harbourview P1 pattern. Used when no file path is set.",
            "config": None,
            "configured": True,
        },
        {
            "id": "graph_inbox",
            "label": "M365 Guest Services Inbox",
            "status": "stub",
            "production_ready": False,
            "description": "Microsoft Graph API — guest services mailbox.",
            "config": "AZURE_TENANT_ID, AZURE_CLIENT_ID (not wired yet)",
            "configured": False,
        },
        {
            "id": "graph_kpi",
            "label": "M365 Staff KPI Emails",
            "status": "stub",
            "production_ready": False,
            "description": "Staff weekly KPI submissions via Graph.",
            "config": "AZURE_* (not wired yet)",
            "configured": False,
        },
        {
            "id": "graph_disruption",
            "label": "M365 Disruption Notifications",
            "status": "stub",
            "production_ready": False,
            "description": "Site disruption / evacuation alerts from operations inbox.",
            "config": "AZURE_* (not wired yet)",
            "configured": False,
        },
        {
            "id": "teams_webhook",
            "label": "Microsoft Teams alerts",
            "status": "active" if settings.teams_webhook_url else "simulated",
            "production_ready": True,
            "description": "POST P1/P2 alerts to a Teams channel webhook. Without this, alerts appear in-app only.",
            "config": "TEAMS_WEBHOOK_URL",
            "configured": bool(settings.teams_webhook_url),
        },
    ]
