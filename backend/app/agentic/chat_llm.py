"""OpenAI-powered conversational chat — multi-turn, tool-using, naturally phrased."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.agentic.loop import MAX_STEPS, ReActLoop
from app.agentic.references import references_from_tools
from app.agentic.store import append_step, complete_run, create_run
from app.agentic.tools import TOOL_REGISTRY
from app.agentic.triggers import make_trigger
from app.agentic.types import AgentRun, ReasoningStep, Trigger

logger = logging.getLogger(__name__)

CHAT_SYSTEM = """You are Insight Assistant — an AI analyst for cinema guest-feedback operations.

You help managers understand prioritised issues, per-site performance, guest comments, SLA status, trends, and root causes.

Rules:
1. For factual questions, call the provided tools first. You may call several tools in sequence.
2. NEVER invent numbers, priorities, site names, or quotes — only use values returned by tools.
3. Answer naturally and conversationally. Match the user's tone. Use short lists when helpful.
4. If data is missing, say so plainly and suggest what they could ask instead.
5. Internal operations briefing only — do not tell the user to contact guests.
6. Pass the week parameter to tools when the user is asking about a specific reporting week.
"""


def _openai_tool_specs() -> list[dict]:
    specs = []
    for name, meta in TOOL_REGISTRY.items():
        properties: dict[str, Any] = {}
        for key, typ in meta["input_schema"].items():
            if typ == "int":
                properties[key] = {"type": "integer", "description": key}
            else:
                properties[key] = {"type": "string", "description": key}
        specs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "additionalProperties": False,
                },
            },
        })
    return specs


def _build_messages(question: str, history: list[dict[str, str]], week: str | None) -> list[dict]:
    week_note = f"Current reporting week: {week}." if week else "Use the latest available week from tools."
    messages: list[dict] = [
        {"role": "system", "content": f"{CHAT_SYSTEM}\n\n{week_note}"},
    ]
    for msg in history[-12:]:
        role = msg.get("role", "user")
        if role in ("user", "assistant") and msg.get("content"):
            messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": question})
    return messages


class AIChatEngine:
    """Grounded ReAct chat backed by OpenAI function calling + natural answer synthesis."""

    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._loop = ReActLoop()

    def run(
        self,
        db: Session,
        *,
        question: str,
        history: list[dict[str, str]],
        week: str | None,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        trigger = make_trigger(
            "question",
            "user",
            f"Question: {question[:100]}",
            {"week": week, "question": question, "mode": "ai"},
        )
        run = create_run(db, trigger, question, "conversational")
        tool_results, step_no = self._tool_loop(db, run, question, history, week, ctx, 0)
        answer = self._synthesize(question, history, week, tool_results)
        self._record_final(db, run, step_no, answer)
        complete_run(db, run, answer, "done")
        return {
            "answer": answer,
            "references": references_from_tools(tool_results, week),
            "a2a_correlation_id": run.id,
            "run_id": run.id,
            "tools_used": [t for t, _ in tool_results],
            "agentic_rounds": len(tool_results),
            "mode": "ai",
        }

    def stream(
        self,
        db: Session,
        *,
        question: str,
        history: list[dict[str, str]],
        week: str | None,
        ctx: dict[str, Any],
    ) -> Iterator[dict[str, Any]]:
        trigger = make_trigger(
            "question",
            "user",
            f"Question: {question[:100]}",
            {"week": week, "question": question, "mode": "ai"},
        )
        run = create_run(db, trigger, question, "conversational")
        tool_results, step_no = self._tool_loop(db, run, question, history, week, ctx, 0)

        yield {
            "type": "meta",
            "references": references_from_tools(tool_results, week),
            "a2a_correlation_id": run.id,
            "run_id": run.id,
            "tools_used": [t for t, _ in tool_results],
            "mode": "ai",
        }

        answer_parts: list[str] = []
        for token in self._stream_synthesize(question, history, week, tool_results):
            answer_parts.append(token)
            yield {"type": "token", "content": token}

        answer = "".join(answer_parts)
        self._record_final(db, run, step_no, answer)
        complete_run(db, run, answer, "done")
        yield {"type": "done", "answer": answer}

    def _tool_loop(
        self,
        db: Session,
        run: AgentRun,
        question: str,
        history: list[dict[str, str]],
        week: str | None,
        ctx: dict[str, Any],
        step_no: int,
    ) -> tuple[list[tuple[str, dict]], int]:
        messages = _build_messages(question, history, week)
        tool_results: list[tuple[str, dict]] = []

        for _ in range(MAX_STEPS):
            thought = "Selecting tools or preparing grounded answer"
            step_no = self._loop._record(db, run, step_no, "conversational", "think", thought)

            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=_openai_tool_specs(),
                tool_choice="auto",
                temperature=0.3,
            )
            msg = resp.choices[0].message

            if not msg.tool_calls:
                if msg.content and not tool_results:
                    return [], step_no
                break

            messages.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                tool = tc.function.name
                raw_args = json.loads(tc.function.arguments or "{}")
                merged = {**ctx, **raw_args}
                if week and "week" not in merged:
                    merged["week"] = week
                step_no, result = self._loop._act(db, run, "conversational", step_no, tool, merged)
                tool_results.append((tool, result))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)[:6000],
                })

        return tool_results, step_no

    def _synthesize(
        self,
        question: str,
        history: list[dict[str, str]],
        week: str | None,
        tool_results: list[tuple[str, dict]],
    ) -> str:
        if not tool_results:
            return self._direct_reply(question, history, week)

        evidence = [
            {"tool": tool, "data": data}
            for tool, data in tool_results
        ]
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0.4,
            messages=[
                {"role": "system", "content": (
                    "Write a clear, conversational answer for the cinema ops manager. "
                    "Use ONLY facts from the tool evidence JSON. Do not invent numbers. "
                    "Be concise but natural — not robotic templates."
                )},
                {"role": "user", "content": json.dumps({
                    "question": question,
                    "week": week,
                    "recent_history": history[-4:],
                    "tool_evidence": evidence,
                })},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or "I retrieved the data but could not phrase an answer — check Agent Activity for the trace."

    def _stream_synthesize(
        self,
        question: str,
        history: list[dict[str, str]],
        week: str | None,
        tool_results: list[tuple[str, dict]],
    ) -> Iterator[str]:
        if not tool_results:
            text = self._direct_reply(question, history, week)
            yield text
            return

        evidence = [{"tool": tool, "data": data} for tool, data in tool_results]
        stream = self.client.chat.completions.create(
            model=self.model,
            temperature=0.4,
            stream=True,
            messages=[
                {"role": "system", "content": (
                    "Write a clear, conversational answer for the cinema ops manager. "
                    "Use ONLY facts from the tool evidence JSON. Do not invent numbers."
                )},
                {"role": "user", "content": json.dumps({
                    "question": question,
                    "week": week,
                    "recent_history": history[-4:],
                    "tool_evidence": evidence,
                })},
            ],
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def _direct_reply(self, question: str, history: list[dict[str, str]], week: str | None) -> str:
        messages = _build_messages(question, history, week)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5,
        )
        return (resp.choices[0].message.content or "").strip()

    def _record_final(self, db: Session, run: AgentRun, step_no: int, answer: str) -> None:
        step = ReasoningStep(
            run_id=run.id,
            step_no=step_no,
            agent="conversational",
            phase="final",
            thought="AI composed grounded natural-language answer",
            action=None,
            observation=answer[:500],
            ts=datetime.utcnow(),
        )
        append_step(db, run, step)
