"""A2A message helpers for orchestrator pipeline stages."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.a2a.bus import get_bus


class PipelineA2A:
    def __init__(self, db: Session, correlation_id: str):
        self.db = db
        self.correlation_id = correlation_id
        self.bus = get_bus()

    def handoff(self, from_agent: str, to_agent: str, summary: str, payload_ref: str | None = None) -> None:
        self.bus.send(
            self.db,
            correlation_id=self.correlation_id,
            from_agent=from_agent,
            to_agent=to_agent,
            intent="handoff",
            summary=summary,
            status="sent",
            payload_ref=payload_ref,
        )
        self.bus.send(
            self.db,
            correlation_id=self.correlation_id,
            from_agent=to_agent,
            to_agent="broadcast",
            intent="status",
            summary=f"{to_agent} processing",
            status="processing",
        )

    def done(self, agent: str, summary: str, payload_ref: str | None = None) -> None:
        self.bus.send(
            self.db,
            correlation_id=self.correlation_id,
            from_agent=agent,
            to_agent="broadcast",
            intent="status",
            summary=summary,
            status="done",
            payload_ref=payload_ref,
        )

    def alert(self, from_agent: str, summary: str, payload_ref: str | None = None) -> None:
        self.bus.send(
            self.db,
            correlation_id=self.correlation_id,
            from_agent=from_agent,
            to_agent="broadcast",
            intent="alert",
            summary=summary,
            status="sent",
            payload_ref=payload_ref,
        )

    def error(self, agent: str, summary: str) -> None:
        self.bus.send(
            self.db,
            correlation_id=self.correlation_id,
            from_agent=agent,
            to_agent="broadcast",
            intent="status",
            summary=summary,
            status="error",
        )
