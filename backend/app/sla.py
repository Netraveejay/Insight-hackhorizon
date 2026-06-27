from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def compute_sla(priority: str, triggered_at: datetime, sla_rules: dict[str, Any]) -> dict[str, Any]:
    """Compute response/resolution deadlines and current SLA status."""
    cfg = sla_rules.get(priority, sla_rules.get("P3", {}))
    response_hours = int(cfg.get("response_hours", 48))
    resolution_hours = int(cfg.get("resolution_hours", 168))

    response_due = triggered_at + timedelta(hours=response_hours)
    resolution_due = triggered_at + timedelta(hours=resolution_hours)
    now = datetime.utcnow()

    if now >= resolution_due:
        status = "breached"
        phase = "resolution"
    elif now >= response_due:
        status = "at_risk"
        phase = "resolution"
    else:
        status = "on_track"
        phase = "response"

    hours_to_response = max(0, (response_due - now).total_seconds() / 3600)
    hours_to_resolution = max(0, (resolution_due - now).total_seconds() / 3600)

    return {
        "priority": priority,
        "triggered_at": triggered_at.isoformat(),
        "response_due_at": response_due.isoformat(),
        "resolution_due_at": resolution_due.isoformat(),
        "response_hours": response_hours,
        "resolution_hours": resolution_hours,
        "status": status,
        "phase": phase,
        "hours_to_response": round(hours_to_response, 1),
        "hours_to_resolution": round(hours_to_resolution, 1),
        "label": _sla_label(status, phase, hours_to_response, hours_to_resolution),
    }


def _sla_label(status: str, phase: str, hrs_response: float, hrs_resolution: float) -> str:
    if status == "breached":
        return "SLA breached — resolution deadline passed"
    if status == "at_risk":
        return f"At risk — respond & resolve within {hrs_resolution:.0f}h"
    if phase == "response":
        return f"On track — acknowledge within {hrs_response:.0f}h"
    return f"On track — resolve within {hrs_resolution:.0f}h"
