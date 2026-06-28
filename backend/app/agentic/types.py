from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Trigger(BaseModel):
    id: str
    type: Literal["schedule", "detection", "anomaly", "question", "manual"]
    source: str
    summary: str
    ts: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class ReasoningStep(BaseModel):
    run_id: str
    step_no: int
    agent: str
    phase: Literal["think", "act", "observe", "reflect", "final"]
    thought: str
    action: dict[str, Any] | None = None
    observation: str | None = None
    ts: datetime


class AgentRun(BaseModel):
    id: str
    trigger: Trigger
    goal: str
    runner: str
    status: Literal["running", "done", "error"]
    steps: list[ReasoningStep] = Field(default_factory=list)
    tool_results: list[tuple[str, dict[str, Any]]] = Field(default_factory=list)
    outcome: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
