"""Coordinator — routes Assistant queries to specialists with validation and fallback."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.a2a.bus import get_bus
from app.agents.retrieval import RETRIEVAL_TOOLS

SPECIALIST_FOR_TOOL: dict[str, str] = {
    "get_top_issues": "detection",
    "get_site": "clustering",
    "get_cluster": "clustering",
    "get_theme_trend": "clustering",
    "get_root_cause": "root_cause",
    "get_detections": "detection",
    "get_sla_status": "sla",
    "get_language_mix": "translation",
    "get_positive_themes": "scoring",
    "search_feedback": "ingestion",
    "get_negative_feedback": "scoring",
}

# When primary retrieval is insufficient, coordinator asks another specialist.
FALLBACK_CHAIN: dict[str, list[str]] = {
    "search_feedback": ["get_negative_feedback"],
    "get_top_issues": ["get_negative_feedback"],
    "get_negative_feedback": ["search_feedback"],
}


def _count_records(result: dict) -> int:
    for key in ("count", "items", "matches", "detections", "clusters"):
        val = result.get(key)
        if isinstance(val, list):
            return len(val)
        if isinstance(val, int):
            return val
    return 0


def _wants_comment_text(question: str) -> bool:
    q = question.lower()
    return any(
        w in q
        for w in (
            "comment",
            "comments",
            "feedback",
            "quote",
            "said",
            "guest said",
            "verbatim",
            "negative comment",
            "complaint",
        )
    )


def _validate(tool_name: str, result: dict, question: str) -> tuple[bool, str]:
    """Return (ok, reason) — coordinator rejects weak results before answering."""
    count = _count_records(result)

    if tool_name == "get_negative_feedback":
        if count == 0:
            return False, "No negative comments in scored data for this week"
        return True, ""

    if tool_name == "search_feedback":
        if count == 0 and _wants_comment_text(question):
            return False, f"No feedback matched query text"
        return True, ""

    if tool_name == "get_top_issues" and _wants_comment_text(question):
        return False, "Overview stats do not include individual comment text"

    if tool_name in ("get_site", "get_detections", "get_sla_status") and count == 0:
        return False, f"{tool_name} returned no records"

    return True, ""


def _fallback_args(tool_name: str, original_args: dict, question: str) -> dict:
    args = dict(original_args)
    if tool_name == "get_negative_feedback":
        if "limit" not in args:
            args["limit"] = 3
    elif tool_name == "search_feedback":
        args["text"] = question
        args.setdefault("limit", 5)
    return args


class RetrievalCoordinator:
    """Message-driven retrieval — emits real A2A traffic and reverts on bad results."""

    def execute(
        self,
        db: Session,
        correlation_id: str,
        tool_name: str,
        args: dict,
        question: str = "",
    ) -> tuple[dict, list[str]]:
        chain = [tool_name]
        current_tool = tool_name
        current_args = dict(args)

        for attempt in range(3):
            specialist = SPECIALIST_FOR_TOOL.get(current_tool, "coordinator")
            self._emit_query(db, correlation_id, current_tool, specialist, current_args)

            fn = RETRIEVAL_TOOLS[current_tool]
            result = fn(db, **current_args)
            ok, reason = _validate(current_tool, result, question)

            if ok:
                self._emit_response(db, correlation_id, specialist, current_tool, result)
                return result, chain

            fallbacks = FALLBACK_CHAIN.get(current_tool, [])
            if attempt >= len(fallbacks):
                self._emit_alert(
                    db,
                    correlation_id,
                    specialist,
                    f"Rejected {current_tool}: {reason}",
                )
                self._emit_response(db, correlation_id, specialist, current_tool, result, status="error")
                return result, chain

            next_tool = fallbacks[attempt]
            self._emit_alert(
                db,
                correlation_id,
                "coordinator",
                f"Revert {current_tool} → {next_tool}: {reason}",
            )
            chain.append(next_tool)
            current_tool = next_tool
            current_args = _fallback_args(next_tool, args, question)

        return result, chain

    def _emit_query(self, db: Session, cid: str, tool: str, specialist: str, args: dict) -> None:
        bus = get_bus()
        bus.send(
            db,
            correlation_id=cid,
            from_agent="assistant",
            to_agent="coordinator",
            intent="query",
            summary=f"Assistant requests {tool}",
            status="sent",
            payload_ref=tool,
        )
        bus.send(
            db,
            correlation_id=cid,
            from_agent="coordinator",
            to_agent=specialist,
            intent="query",
            summary=f"Hand off {tool} {json.dumps(args)[:72]}",
            status="processing",
            payload_ref=tool,
        )

    def _emit_response(
        self,
        db: Session,
        cid: str,
        specialist: str,
        tool: str,
        result: dict,
        status: str = "done",
    ) -> None:
        count = _count_records(result)
        bus = get_bus()
        bus.send(
            db,
            correlation_id=cid,
            from_agent=specialist,
            to_agent="coordinator",
            intent="response",
            summary=f"{tool}: {count} record(s)" if count else f"{tool}: empty",
            status=status,
            payload_ref=tool,
        )
        bus.send(
            db,
            correlation_id=cid,
            from_agent="coordinator",
            to_agent="assistant",
            intent="response",
            summary=f"Grounded payload for {tool}",
            status=status,
            payload_ref=tool,
        )

    def _emit_alert(self, db: Session, cid: str, from_agent: str, summary: str) -> None:
        get_bus().send(
            db,
            correlation_id=cid,
            from_agent=from_agent,
            to_agent="assistant",
            intent="alert",
            summary=summary,
            status="error",
            payload_ref=None,
        )


_coordinator: RetrievalCoordinator | None = None


def get_coordinator() -> RetrievalCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = RetrievalCoordinator()
    return _coordinator
