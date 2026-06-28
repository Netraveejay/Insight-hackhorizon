from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class A2AMessage(BaseModel):
    id: str
    ts: datetime
    correlation_id: str
    from_agent: str
    to_agent: str
    intent: Literal["handoff", "query", "response", "alert", "status"]
    summary: str
    status: Literal["sent", "processing", "done", "error"]
    payload_ref: str | None = None


class AgentDefinition(BaseModel):
    id: str
    name: str
    type: Literal["orchestrator", "connector", "deterministic", "llm", "coordinator", "assistant"]
    role: str
    layout_x: float = 0
    layout_y: float = 0
