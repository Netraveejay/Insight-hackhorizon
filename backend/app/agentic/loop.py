"""ReAct-style reasoning loop — LLM or deterministic driver, always traced."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.a2a.bus import get_bus
from app.agentic.store import append_step, complete_run, create_run, summarize_observation
from app.agentic.tools import TOOL_REGISTRY, call_tool, tool_agent
from app.agentic.types import AgentRun, ReasoningStep, Trigger
from app.config import get_settings
from app.schemas import SITE_BY_ID

logger = logging.getLogger(__name__)

MAX_STEPS = 8


class ReActLoop:
    """Observe → think → act loop with streamed reasoning steps."""

    def run(
        self,
        db: Session,
        *,
        trigger: Trigger,
        goal: str,
        runner: str,
        context: dict[str, Any] | None = None,
        plan: list[dict[str, Any]] | None = None,
    ) -> AgentRun:
        ctx = context or {}
        run = create_run(db, trigger, goal, runner)
        settings = get_settings()
        step_no = 0
        observations: list[tuple[str, dict]] = []
        outcome = ""

        try:
            if plan:
                outcome = self._run_deterministic_plan(db, run, runner, plan, ctx, step_no)
            elif settings.openai_api_key:
                outcome, step_no = self._run_llm(db, run, runner, goal, ctx, settings.openai_api_key, step_no)
            else:
                outcome = self._run_deterministic_goal(db, run, runner, goal, ctx, trigger)
            complete_run(db, run, outcome, "done")
        except Exception as e:
            logger.exception("Agent run failed: %s", e)
            outcome = f"Run ended with error: {e}"
            complete_run(db, run, outcome, "error")

        return run

    def _record(
        self,
        db: Session,
        run: AgentRun,
        step_no: int,
        agent: str,
        phase: str,
        thought: str,
        action: dict | None = None,
        observation: str | None = None,
    ) -> int:
        step = ReasoningStep(
            run_id=run.id,
            step_no=step_no,
            agent=agent,
            phase=phase,  # type: ignore[arg-type]
            thought=thought,
            action=action,
            observation=observation,
            ts=datetime.utcnow(),
        )
        append_step(db, run, step)
        return step_no + 1

    def _act(self, db: Session, run: AgentRun, runner: str, step_no: int, tool: str, inputs: dict) -> tuple[int, dict]:
        specialist = tool_agent(tool)
        thought = f"Call {tool} to gather grounded data"
        step_no = self._record(db, run, step_no, runner, "think", thought)
        action = {"tool": tool, "input": inputs}
        step_no = self._record(db, run, step_no, runner, "act", thought, action=action)
        get_bus().send(
            db,
            correlation_id=run.id,
            from_agent=runner,
            to_agent=specialist,
            intent="query",
            summary=f"{tool} {json.dumps(inputs)[:80]}",
            status="processing",
            payload_ref=tool,
        )
        try:
            result = call_tool(db, tool, inputs)
            obs = summarize_observation(tool, result)
        except Exception as e:
            result = {"error": str(e)}
            obs = f"Tool error: {e}"
        get_bus().send(
            db,
            correlation_id=run.id,
            from_agent=specialist,
            to_agent=runner,
            intent="response",
            summary=obs[:120],
            status="done" if "error" not in result else "error",
            payload_ref=tool,
        )
        step_no = self._record(db, run, step_no, runner, "observe", thought, observation=obs)
        return step_no, result

    def _run_deterministic_plan(
        self,
        db: Session,
        run: AgentRun,
        runner: str,
        plan: list[dict[str, Any]],
        ctx: dict,
        step_no: int,
    ) -> str:
        results: list[tuple[str, dict]] = []
        for item in plan[:MAX_STEPS]:
            tool = item["tool"]
            inputs = {**ctx, **item.get("input", {})}
            step_no, result = self._act(db, run, runner, step_no, tool, inputs)
            results.append((tool, result))
        run.tool_results = results
        return self._compose_outcome(run.runner, run.goal, results, ctx)

    def _run_deterministic_goal(
        self,
        db: Session,
        run: AgentRun,
        runner: str,
        goal: str,
        ctx: dict,
        trigger: Trigger,
    ) -> str:
        plan = _plan_for_goal(runner, goal, ctx, trigger)
        return self._run_deterministic_plan(db, run, runner, plan, ctx, 0)

    def _run_llm(
        self,
        db: Session,
        run: AgentRun,
        runner: str,
        goal: str,
        ctx: dict,
        api_key: str,
        step_no: int,
    ) -> tuple[str, int]:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        tool_specs = [
            {
                "name": name,
                "description": meta["description"],
                "parameters": {"type": "object", "properties": {k: {"type": "string"} for k in meta["input_schema"]}},
            }
            for name, meta in TOOL_REGISTRY.items()
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a read-only cinema ops analyst. Use tools only. "
                    "Never invent numbers. When done, reply DONE: followed by a grounded briefing."
                ),
            },
            {"role": "user", "content": f"Goal: {goal}\nContext: {json.dumps(ctx)}"},
        ]
        results: list[tuple[str, dict]] = []
        for _ in range(MAX_STEPS):
            step_no = self._record(
                db, run, step_no, runner, "think", "LLM selecting next tool or final answer"
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=[{"type": "function", "function": t} for t in tool_specs],
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            if msg.content and msg.content.strip().upper().startswith("DONE:"):
                return msg.content.split(":", 1)[-1].strip()
            if not msg.tool_calls:
                return msg.content or self._compose_outcome(runner, goal, results, ctx)
            for tc in msg.tool_calls:
                tool = tc.function.name
                inputs = json.loads(tc.function.arguments or "{}")
                inputs = {**ctx, **inputs}
                step_no, result = self._act(db, run, runner, step_no, tool, inputs)
                results.append((tool, result))
                messages.append(msg.model_dump())
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)[:4000],
                })
        run.tool_results = results
        return self._compose_outcome(runner, goal, results, ctx)

    def _compose_outcome(
        self,
        runner: str,
        goal: str,
        results: list[tuple[str, dict]],
        ctx: dict,
    ) -> str:
        if runner == "investigator":
            return _investigator_briefing(results, ctx)
        if runner == "conversational":
            return _conversational_answer(goal, results)
        if runner == "coordinator":
            return _coordinator_summary(results, ctx)
        if runner == "critic":
            return _critic_summary(results)
        parts = [f"Goal: {goal}"]
        for tool, data in results:
            parts.append(f"- {tool}: {summarize_observation(tool, data)}")
        return "\n".join(parts)


def _plan_for_goal(runner: str, goal: str, ctx: dict, trigger: Trigger) -> list[dict[str, Any]]:
    week = ctx.get("week")
    payload = trigger.payload or {}

    if runner == "investigator":
        cid = payload.get("cluster_id") or ctx.get("cluster_id")
        site_id = payload.get("site_id") or ctx.get("site_id")
        theme = payload.get("theme") or ctx.get("theme", "projection_quality")
        plan: list[dict[str, Any]] = [
            {"tool": "get_cluster", "input": {"cluster_id": cid, "week": week}},
            {"tool": "get_root_cause", "input": {"cluster_id": cid, "week": week}},
            {"tool": "correlate_with_staff", "input": {"site_id": site_id, "theme": theme, "week": week}},
            {"tool": "check_contagion", "input": {"theme": theme, "week": week}},
        ]
        if site_id:
            other = "northgate" if site_id == "harbourview" else "harbourview"
            plan.append({"tool": "compare_sites", "input": {"site_a": site_id, "site_b": other, "week": week}})
        return plan

    if runner == "conversational":
        return _plan_question(goal, ctx)

    if runner == "coordinator":
        return [{"tool": "get_top_issues", "input": {"week": week}}, {"tool": "get_detections", "input": {"week": week, "kind": "cross_source"}}]

    return [{"tool": "get_top_issues", "input": {"week": week}}]


def _parse_limit(q: str, default: int = 3) -> int:
    m = re.search(r"(?:top|first|bottom|last|least|lowest)\s+(\d+)", q)
    if m:
        return min(int(m.group(1)), 10)
    m = re.search(r"\b(\d+)\s+(?:issue|issues|priority|priorities)\b", q)
    if m:
        return min(int(m.group(1)), 10)
    return default


def _is_least_priority(q: str) -> bool:
    return bool(re.search(r"\b(least|lowest|bottom|minor)\b", q))


def _is_issue_list_question(q: str) -> bool:
    return bool(re.search(r"\b(issue|issues|priority|priorities)\b", q))


def _plan_question(goal: str, ctx: dict) -> list[dict[str, Any]]:
    q = (ctx.get("question") or goal).lower()
    week = ctx.get("week")
    limit = _parse_limit(q, 3)

    if re.search(r"\b(negative|comment|comments|complaint|quote)\b", q) and "positive" not in q:
        inp: dict[str, Any] = {"week": week, "limit": limit}
        for site in ("harbourview", "northgate", "lakeside", "riverside"):
            if site in q:
                inp["site_id"] = site
                break
        return [{"tool": "get_negative_feedback", "input": inp}]

    if re.search(r"\b(sla|breach)\b", q):
        return [{"tool": "get_sla_status", "input": {"week": week}}]

    if "cross" in q and "source" in q:
        return [{"tool": "get_detections", "input": {"week": week, "kind": "cross_source"}}]

    if re.search(r"\b(why|root cause)\b", q) and not _is_issue_list_question(q):
        site = next((s for s in ("harbourview", "northgate", "lakeside", "riverside") if s in q), None)
        if not site:
            site = ctx.get("site_id", "harbourview")
        return [{"tool": "get_root_cause", "input": {"cluster_id": ctx.get("cluster_id"), "week": week}}] if ctx.get("cluster_id") else [
            {"tool": "get_site", "input": {"site_id": site, "week": week}},
        ]

    if re.search(r"\b(language|multilingual)\b", q):
        return [{"tool": "get_language_mix", "input": {"week": week}}]

    if "positive" in q:
        return [{"tool": "get_positive_themes", "input": {"week": week}}]

    if re.search(r"\b(spreading|contagion|other sites)\b", q):
        theme = "projection_quality" if "projection" in q else "ticketing_queue"
        return [
            {"tool": "get_root_cause", "input": {"cluster_id": ctx.get("cluster_id"), "week": week}},
            {"tool": "check_contagion", "input": {"theme": theme, "week": week}},
        ]

    if re.search(r"\b(compare|versus| vs )\b", q):
        return [{"tool": "compare_sites", "input": {"site_a": "harbourview", "site_b": "northgate", "week": week}}]

    site_names = ("harbourview", "northgate", "lakeside", "riverside", "westgate")
    if any(site in q for site in site_names) and not _is_issue_list_question(q):
        site = next(s for s in site_names if s in q)
        return [{"tool": "get_site", "input": {"site_id": site, "week": week}}]

    if _is_issue_list_question(q) or re.search(r"\b(top|worst|biggest|main)\b", q):
        return [{"tool": "get_top_issues", "input": {"week": week}}]

    return [{"tool": "get_top_issues", "input": {"week": week}}]


def _investigator_briefing(results: list[tuple[str, dict]], ctx: dict) -> str:
    lines = ["## P1 Investigation Briefing", ""]
    cluster = root = staff = contagion = None
    for tool, data in results:
        if tool == "get_cluster":
            cluster = data
        elif tool == "get_root_cause":
            root = data
        elif tool == "correlate_with_staff":
            staff = data
        elif tool == "check_contagion":
            contagion = data

    if cluster and cluster.get("cluster"):
        c = cluster["cluster"]
        site = SITE_BY_ID.get(c.get("site_id", ""), {}).get("name", c.get("site_id"))
        lines.append(f"**What:** {site} — {c.get('theme', '').replace('_', ' ')} ({c.get('neg', 0)} negatives this week).")

    if root and root.get("found"):
        rc = root["root_cause"]
        lines.append(f"**Likely cause:** {rc.get('category')} — {rc.get('summary')}.")
        lines.append(f"**Suggested owner:** Technical Operations (from taxonomy).")

    if staff:
        lines.append(
            f"**Cross-source:** guest negatives={staff.get('guest_neg')}, staff signals={staff.get('staff_neg')}, "
            f"aligned={staff.get('aligned')}."
        )

    if contagion:
        spread = "spreading across sites" if contagion.get("spreading") else "localised to one site"
        lines.append(f"**Spread:** {contagion.get('site_count')} site(s) — issue is {spread}.")

    lines.append("")
    lines.append("*Internal briefing only — do not contact guests.*")
    return "\n".join(lines)


def _conversational_answer(goal: str, results: list[tuple[str, dict]]) -> str:
    q = goal.lower()
    limit = _parse_limit(q, 3)
    least = _is_least_priority(q)
    parts: list[str] = []
    for tool, data in results:
        if tool == "get_negative_feedback":
            items = data.get("items", [])
            if items:
                parts.append(f"Top {len(items)} negative comment(s) for {data.get('week')}:")
                for i, item in enumerate(items, 1):
                    snippet = item["text"][:140].rstrip()
                    parts.append(
                        f"{i}. {item['site_name']} ({item['theme'].replace('_', ' ')}): \"{snippet}\""
                    )
            else:
                parts.append("No negative comments found for that week.")
        elif tool == "get_top_issues":
            ov = data.get("overview", {})
            ranked = list(ov.get("ranked_actions", []))
            if least:
                ranked = list(reversed(ranked))
            if ranked:
                heading = "Lowest priority issues" if least else "Top priority issues"
                n = min(limit, len(ranked))
                parts.append(f"{heading} for {data.get('week')}:")
                for i, r in enumerate(ranked[:n], 1):
                    parts.append(
                        f"{i}. {r['site_name']} — {r['theme'].replace('_', ' ')} "
                        f"({r.get('priority')}, {r.get('neg')} negatives)"
                    )
            else:
                parts.append(f"No open priority issues for {data.get('week')}.")
        elif tool == "get_site":
            clusters = data.get("clusters", [])
            site_name = data.get("site_name", "Site")
            if clusters:
                top = clusters[0]
                parts.append(
                    f"{site_name} top issue: {top['theme'].replace('_', ' ')} "
                    f"({top['neg']} negatives"
                    + (f", {top['priority']}" if top.get("priority") else "")
                    + ")."
                )
            else:
                parts.append(f"No negative clusters for {site_name} in {data.get('week', 'this week')}.")
        elif tool == "get_sla_status":
            sm = data.get("summary", {})
            parts.append(
                f"SLA: {sm.get('on_track', 0)} on track, {sm.get('at_risk', 0)} at risk, "
                f"{sm.get('breached', 0)} breached."
            )
        elif tool == "get_detections":
            items = data.get("detections", [])
            if items:
                desc = "; ".join(
                    f"{i['site_name']} {i['theme'].replace('_', ' ')}" for i in items[:3]
                )
                parts.append(f"Found {len(items)} detection(s): {desc}.")
        elif tool == "check_contagion":
            parts.append(
                f"Theme {data.get('theme')} appears at {data.get('site_count')} site(s); "
                f"spreading={data.get('spreading')}."
            )
        elif tool == "get_root_cause" and data.get("found"):
            rc = data["root_cause"]
            parts.append(f"Root cause: {rc.get('category')} — {rc.get('summary')}.")
        elif tool == "compare_sites":
            a = data.get("site_a", {})
            b = data.get("site_b", {})
            parts.append(
                f"Compare: {a.get('site_name')} vs {b.get('site_name')} — see cluster counts in trace."
            )
        elif tool == "get_language_mix":
            langs = data.get("languages", [])
            if langs:
                mix = ", ".join(f"{l['language']} ({l['count']})" for l in langs[:5])
                parts.append(f"Languages: {mix}.")
        else:
            parts.append(summarize_observation(tool, data))
    if not parts:
        return "I don't have computed data covering that question."
    return "\n".join(parts)


def _coordinator_summary(results: list[tuple[str, dict]], ctx: dict) -> str:
    lines = [f"Pipeline coordination complete for week {ctx.get('week', 'n/a')}."]
    for tool, data in results:
        lines.append(f"- {summarize_observation(tool, data)}")
    return "\n".join(lines)


def _critic_summary(results: list[tuple[str, dict]]) -> str:
    return "Critic review complete."
