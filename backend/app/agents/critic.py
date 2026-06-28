"""Critic agent — rejects ungrounded or off-topic answers; triggers planner revision."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.a2a.bus import get_bus


def _wants_negative_comments(q: str) -> bool:
    return bool(
        re.search(r"\b(negative|complaint|comment|comments|quote|verbatim|guest said)\b", q)
        and "positive" not in q
    )


def _wants_issues_list(q: str) -> bool:
    return bool(re.search(r"\b(top|issue|issues|problem|priority|flag)\b", q)) and not _wants_negative_comments(q)


def _record_count(tool_name: str, data: dict) -> int:
    if tool_name == "get_top_issues":
        ov = data.get("overview", {})
        return len(ov.get("ranked_actions", [])) or (1 if ov.get("hero_issue") else 0)
    for key in ("count", "items", "matches", "detections", "clusters"):
        val = data.get(key)
        if isinstance(val, list):
            return len(val)
        if isinstance(val, int):
            return val
    return 0


class CriticAgent:
    """Reviews assistant drafts — read-only; never invents data."""

    MAX_ROUNDS = 3

    def evaluate(
        self,
        db: Session,
        correlation_id: str,
        question: str,
        answer: str,
        tool_results: list[tuple[str, dict]],
        tools_used: list[str],
        week: str | None,
    ) -> dict[str, Any]:
        get_bus().send(
            db,
            correlation_id=correlation_id,
            from_agent="assistant",
            to_agent="critic",
            intent="query",
            summary="Review draft answer for grounding and relevance",
            status="processing",
            payload_ref="critique",
        )

        verdict = self._check(question, answer, tool_results, tools_used, week)

        if verdict["ok"]:
            get_bus().send(
                db,
                correlation_id=correlation_id,
                from_agent="critic",
                to_agent="assistant",
                intent="response",
                summary=f"Approved: {verdict['reason']}",
                status="done",
                payload_ref="critique",
            )
        else:
            get_bus().send(
                db,
                correlation_id=correlation_id,
                from_agent="critic",
                to_agent="planner",
                intent="alert",
                summary=f"Reject: {verdict['reason']}",
                status="error",
                payload_ref="critique",
            )

        return verdict

    def _check(
        self,
        question: str,
        answer: str,
        tool_results: list[tuple[str, dict]],
        tools_used: list[str],
        week: str | None,
    ) -> dict[str, Any]:
        q = question.lower()
        ans = answer.lower()

        if not answer.strip() or "don't have computed data" in ans:
            alt = self._fallback_tools(q, tools_used, week)
            if alt:
                return {"ok": False, "reason": "No grounded data in draft", "revise_tools": alt}
            return {"ok": True, "reason": "Honestly reported missing data"}

        total_records = sum(_record_count(t, d) for t, d in tool_results)
        if total_records == 0 and tool_results:
            alt = self._fallback_tools(q, tools_used, week)
            if alt:
                return {"ok": False, "reason": "Retrieval returned empty", "revise_tools": alt}

        if _wants_negative_comments(q):
            if "get_negative_feedback" not in tools_used:
                limit = 3
                m = re.search(r"(?:top|first)\s+(\d+)", q)
                if m:
                    limit = min(int(m.group(1)), 10)
                return {
                    "ok": False,
                    "reason": "Question asks for comment text, not overview stats",
                    "revise_tools": [{"name": "get_negative_feedback", "args": {"week": week, "limit": limit}}],
                }
            if not re.search(r'\d+\.\s|".{10,}"', answer):
                return {
                    "ok": False,
                    "reason": "Answer should list quoted comment text",
                    "revise_tools": [{"name": "get_negative_feedback", "args": {"week": week, "limit": 3}}],
                }

        if _wants_issues_list(q) and "get_top_issues" in tools_used:
            if "priority" not in ans and "issue" not in ans and "harbourview" not in ans:
                return {
                    "ok": False,
                    "reason": "Answer missing ranked issues",
                    "revise_tools": [{"name": "get_top_issues", "args": {"week": week}}],
                }

        if re.search(r"\b(sla|breach)\b", q) and "sla" not in ans and "track" not in ans:
            return {
                "ok": False,
                "reason": "SLA question needs SLA metrics",
                "revise_tools": [{"name": "get_sla_status", "args": {"week": week}}],
            }

        if ("cross" in q and "source" in q) or "compounding" in q:
            if "detection" not in ans and "found" not in ans and "cross" not in ans:
                kind = "compounding" if "compounding" in q else "cross_source"
                return {
                    "ok": False,
                    "reason": "Detection flags expected",
                    "revise_tools": [{"name": "get_detections", "args": {"week": week, "kind": kind}}],
                }

        if re.search(r"\b(language|multilingual|translated)\b", q) and "language" not in ans:
            return {
                "ok": False,
                "reason": "Language mix expected",
                "revise_tools": [{"name": "get_language_mix", "args": {"week": week}}],
            }

        return {"ok": True, "reason": "Grounded and matches question intent"}

    def _fallback_tools(self, q: str, tools_used: list[str], week: str | None) -> list[dict]:
        if _wants_negative_comments(q) and "get_negative_feedback" not in tools_used:
            return [{"name": "get_negative_feedback", "args": {"week": week, "limit": 3}}]
        if _wants_issues_list(q) and "get_top_issues" not in tools_used:
            return [{"name": "get_top_issues", "args": {"week": week}}]
        if "search" in q and "search_feedback" not in tools_used:
            return [{"name": "search_feedback", "args": {"text": q, "week": week}}]
        return []
