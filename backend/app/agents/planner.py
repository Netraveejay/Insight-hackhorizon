"""Planner agent — decides which retrieval tools to invoke (LLM or deterministic router)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.a2a.bus import get_bus


class PlannerAgent:
    """Plans read-only retrieval steps; emits A2A handoffs."""

    def plan(
        self,
        db: Session,
        correlation_id: str,
        question: str,
        history: list[dict],
        week: str | None,
        plan_fn,
        *,
        round_num: int = 1,
    ) -> dict:
        get_bus().send(
            db,
            correlation_id=correlation_id,
            from_agent="assistant",
            to_agent="planner",
            intent="query",
            summary=f"Round {round_num}: plan retrieval for «{question[:72]}»",
            status="processing",
            payload_ref="plan",
        )
        plan = plan_fn(question, history, week)
        tool_names = [t["name"] for t in plan.get("tools", [])]
        get_bus().send(
            db,
            correlation_id=correlation_id,
            from_agent="planner",
            to_agent="coordinator",
            intent="handoff",
            summary=f"Execute: {', '.join(tool_names) or 'none'}",
            status="done",
            payload_ref=",".join(tool_names),
        )
        return plan

    def announce_revision(self, db: Session, correlation_id: str, reason: str, tools: list[str]) -> None:
        get_bus().send(
            db,
            correlation_id=correlation_id,
            from_agent="planner",
            to_agent="coordinator",
            intent="handoff",
            summary=f"Revised plan ({reason}): {', '.join(tools)}",
            status="processing",
            payload_ref="revise",
        )
