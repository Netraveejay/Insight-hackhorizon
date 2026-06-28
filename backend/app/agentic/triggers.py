"""Trigger bus — routes events to reasoning agents."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from app.agentic.types import Trigger


def make_trigger(
    type: Literal["schedule", "detection", "anomaly", "question", "manual"],
    source: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> Trigger:
    return Trigger(
        id=str(uuid.uuid4())[:12],
        type=type,
        source=source,
        summary=summary,
        ts=datetime.utcnow(),
        payload=payload or {},
    )
