"""Agent-to-agent workflow trace — records orchestrator handoffs between agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


AGENT_LABELS: dict[str, str] = {
    "orchestrator": "Orchestrator",
    "connector": "Data Connector",
    "ingestion": "Ingestion Agent",
    "translation": "Translation Agent",
    "scoring": "Scoring Agent",
    "clustering": "Clustering Agent",
    "detection": "Detection Agent",
    "root_cause": "Root Cause Agent",
    "sla": "SLA Tracker",
    "insight": "Insight Agent",
    "output": "Output Agent",
    "explainability": "Explainability Agent",
}


class AgentMessage(BaseModel):
    id: str
    seq: int
    from_agent: str
    to_agent: str
    from_label: str
    to_label: str
    message_type: str  # request | response | enrichment
    subject: str
    artifact_type: str
    artifact_count: int
    payload_summary: dict[str, Any] = Field(default_factory=dict)
    sample: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str


class AgentWorkflow(BaseModel):
    run_id: str
    week: str
    protocol: str = "orchestrator-led-a2a-v1"
    agents: list[str]
    messages: list[AgentMessage]
    summary: str


class AgentWorkflowRecorder:
    """Collect structured A2A messages during a pipeline run."""

    def __init__(self, run_id: str, week: str):
        self.run_id = run_id
        self.week = week
        self._seq = 0
        self._messages: list[AgentMessage] = []
        self._agents: set[str] = {"orchestrator"}

    def emit(
        self,
        *,
        from_agent: str,
        to_agent: str,
        message_type: str,
        subject: str,
        artifact_type: str,
        artifact_count: int,
        payload_summary: dict[str, Any] | None = None,
        sample: list[Any] | None = None,
    ) -> AgentMessage:
        self._seq += 1
        self._agents.add(from_agent)
        self._agents.add(to_agent)
        msg = AgentMessage(
            id=str(uuid4())[:12],
            seq=self._seq,
            from_agent=from_agent,
            to_agent=to_agent,
            from_label=AGENT_LABELS.get(from_agent, from_agent),
            to_label=AGENT_LABELS.get(to_agent, to_agent),
            message_type=message_type,
            subject=subject,
            artifact_type=artifact_type,
            artifact_count=artifact_count,
            payload_summary=payload_summary or {},
            sample=_sample_items(sample or []),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        self._messages.append(msg)
        return msg

    def request(self, from_agent: str, to_agent: str, **kwargs: Any) -> AgentMessage:
        return self.emit(from_agent=from_agent, to_agent=to_agent, message_type="request", **kwargs)

    def response(self, from_agent: str, to_agent: str, **kwargs: Any) -> AgentMessage:
        return self.emit(from_agent=from_agent, to_agent=to_agent, message_type="response", **kwargs)

    def enrichment(self, from_agent: str, to_agent: str, **kwargs: Any) -> AgentMessage:
        return self.emit(from_agent=from_agent, to_agent=to_agent, message_type="enrichment", **kwargs)

    def build(self) -> AgentWorkflow:
        agents = sorted(
            self._agents,
            key=lambda a: _AGENT_ORDER.index(a) if a in _AGENT_ORDER else 99,
        )
        return AgentWorkflow(
            run_id=self.run_id,
            week=self.week,
            agents=agents,
            messages=self._messages,
            summary=f"{len(self._messages)} agent messages across {len(agents)} participants",
        )


_AGENT_ORDER = [
    "orchestrator",
    "connector",
    "ingestion",
    "translation",
    "scoring",
    "clustering",
    "detection",
    "root_cause",
    "sla",
    "insight",
    "output",
    "explainability",
]


def _sample_items(items: list[Any], limit: int = 2) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items[:limit]:
        if hasattr(item, "model_dump"):
            data = item.model_dump(mode="json")
        elif isinstance(item, dict):
            data = item
        else:
            continue
        out.append(_trim_sample(data))
    return out


def _trim_sample(data: dict[str, Any]) -> dict[str, Any]:
    """Keep samples readable in the UI."""
    text = data.get("text") or data.get("original_text") or data.get("insight")
    if isinstance(text, str) and len(text) > 120:
        text = text[:117] + "..."
    keys = [
        "id",
        "cluster_id",
        "site_id",
        "channel",
        "source_type",
        "week",
        "primary_theme",
        "theme",
        "priority",
        "translated",
        "original_language",
        "neg",
        "volume",
        "confidence_band",
        "owner_suggested",
        "root_cause",
        "sla",
        "compounding",
        "cross_source",
    ]
    sample = {k: data[k] for k in keys if k in data and data[k] is not None}
    if text:
        sample["text"] = text
    return sample
