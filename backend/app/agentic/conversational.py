"""ConversationalAgent — AI chat (OpenAI) or offline ReAct fallback."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agentic.chat_llm import AIChatEngine
from app.agentic.loop import ReActLoop
from app.agentic.references import references_from_tools
from app.agentic.triggers import make_trigger
from app.agentic.types import AgentRun
from app.config import get_settings


class ConversationalAgent:
    def run(
        self,
        db: Session,
        question: str,
        week: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict:
        hist = history or []
        settings = get_settings()

        if settings.openai_api_key:
            ctx = _build_ctx(question, week)
            return AIChatEngine(settings.openai_api_key, settings.openai_model).run(
                db,
                question=question,
                history=hist,
                week=week,
                ctx=ctx,
            )

        return self._run_offline(db, question, week, hist)

    def stream(
        self,
        db: Session,
        question: str,
        week: str | None = None,
        history: list[dict[str, str]] | None = None,
    ):
        hist = history or []
        settings = get_settings()

        if settings.openai_api_key:
            ctx = _build_ctx(question, week)
            yield from AIChatEngine(settings.openai_api_key, settings.openai_model).stream(
                db,
                question=question,
                history=hist,
                week=week,
                ctx=ctx,
            )
            return

        result = self._run_offline(db, question, week, hist)
        yield {
            "type": "meta",
            "references": result["references"],
            "a2a_correlation_id": result["a2a_correlation_id"],
            "run_id": result["run_id"],
            "tools_used": result.get("tools_used", []),
            "mode": "offline",
        }
        words = (result["answer"] or "").split()
        for i, word in enumerate(words):
            yield {"type": "token", "content": word + (" " if i < len(words) - 1 else "")}
        yield {"type": "done", "answer": result["answer"]}

    def _run_offline(
        self,
        db: Session,
        question: str,
        week: str | None,
        hist: list[dict[str, str]],
    ) -> dict:
        trigger = make_trigger(
            "question",
            "user",
            f"Question: {question[:100]}",
            {"week": week, "question": question, "mode": "offline"},
        )
        ctx = _build_ctx(question, week)
        run: AgentRun = ReActLoop().run(
            db,
            trigger=trigger,
            goal=question,
            runner="conversational",
            context=ctx,
        )
        tool_results = run.tool_results or _tool_results_from_run(run)
        return {
            "answer": run.outcome or "",
            "references": references_from_tools(tool_results, week),
            "a2a_correlation_id": run.id,
            "run_id": run.id,
            "tools_used": [s.action.get("tool") for s in run.steps if s.action and s.action.get("tool")],
            "agentic_rounds": len([s for s in run.steps if s.phase == "act"]),
            "mode": "offline",
        }


def _build_ctx(question: str, week: str | None) -> dict:
    ctx: dict = {"week": week, "question": question}
    q_lower = question.lower()
    for site in ("harbourview", "northgate", "lakeside", "riverside", "westgate"):
        if site in q_lower:
            ctx["site_id"] = site
            break
    return ctx


def _tool_results_from_run(run: AgentRun) -> list[tuple[str, dict]]:
    """Best-effort reconstruction for reference links (offline mode)."""
    results: list[tuple[str, dict]] = []
    for step in run.steps:
        if step.phase == "act" and step.action:
            tool = step.action.get("tool")
            if tool:
                results.append((tool, {"summary": step.observation or ""}))
    return results


def assistant_status() -> dict:
    settings = get_settings()
    enabled = bool(settings.openai_api_key)
    return {
        "ai_enabled": enabled,
        "mode": "ai" if enabled else "offline",
        "model": settings.openai_model if enabled else None,
        "message": (
            f"AI assistant active ({settings.openai_model})"
            if enabled
            else "Offline mode — set OPENAI_API_KEY in .env for a real AI chatbot"
        ),
    }
