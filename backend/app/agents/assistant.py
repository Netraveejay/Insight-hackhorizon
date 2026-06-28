"""Conversational Insight Assistant — read-only, grounded, A2A-observable."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.a2a.coordinator import get_coordinator
from app.agents.critic import CriticAgent
from app.agents.planner import PlannerAgent
from app.agents.retrieval import RETRIEVAL_TOOLS
from app.config import get_settings
from app.schemas import SITE_BY_ID

logger = logging.getLogger(__name__)

SUGGESTED_QUESTIONS = [
    "What are the top issues this week?",
    "What are the top 3 negative comments?",
    "How is Harbourview doing?",
    "Why is projection quality bad at Harbourview?",
    "Any cross-source or compounding issues?",
    "What is the SLA status — any breaches?",
    "How is projection quality trending over weeks?",
    "What languages appear in feedback?",
    "What positive themes are strongest?",
    "Summarise this week for leadership",
    "Compare Northgate and Harbourview issues",
]


class ConversationalInsightAgent:
    """Grounded Q&A — agentic plan → retrieve → critique → revise loop."""

    def __init__(self) -> None:
        self._planner = PlannerAgent()
        self._critic = CriticAgent()

    def chat(
        self,
        db: Session,
        messages: list[dict[str, str]],
        week: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        cid = correlation_id or str(uuid.uuid4())[:12]
        question = messages[-1]["content"] if messages else ""
        history = messages[:-1]
        coordinator = get_coordinator()
        tools_used: list[str] = []
        agentic_rounds = 0
        answer = ""
        references: list[dict] = []
        tool_results: list[tuple[str, dict]] = []
        plan: dict = {"tools": []}
        verdict: dict[str, Any] = {"ok": False}

        for round_num in range(1, CriticAgent.MAX_ROUNDS + 1):
            agentic_rounds = round_num
            if round_num == 1:
                plan = self._planner.plan(
                    db, cid, question, history, week, self._plan, round_num=round_num
                )
            else:
                self._planner.announce_revision(
                    db,
                    cid,
                    verdict.get("reason", "critic revision"),
                    [t["name"] for t in plan.get("tools", [])],
                )

            tool_results = []
            for call in plan["tools"]:
                tool_name = call["name"]
                args = call.get("args", {})
                result, chain = coordinator.execute(db, cid, tool_name, args, question=question)
                tools_used.extend(chain)
                tool_results.append((chain[-1], result))

            tool_results = self._maybe_root_cause(db, cid, question, tool_results, coordinator, tools_used)

            answer, references = self._compose_answer(question, tool_results, week)
            verdict = self._critic.evaluate(db, cid, question, answer, tool_results, tools_used, week)

            if verdict.get("ok"):
                break
            revise = verdict.get("revise_tools")
            if not revise:
                break
            plan = {"tools": revise}

        return {
            "answer": answer,
            "references": references,
            "a2a_correlation_id": cid,
            "tools_used": tools_used,
            "agentic_rounds": agentic_rounds,
        }

    def _maybe_root_cause(
        self,
        db: Session,
        cid: str,
        question: str,
        tool_results: list[tuple[str, dict]],
        coordinator,
        tools_used: list[str],
    ) -> list[tuple[str, dict]]:
        if any(k in question.lower() for k in ("why", "root cause")) and not any(
            t == "get_root_cause" for t, _ in tool_results
        ):
            for _tool_name, data in tool_results:
                if data.get("clusters"):
                    cid_cluster = data["clusters"][0]["cluster_id"]
                    rc, chain = coordinator.execute(
                        db,
                        cid,
                        "get_root_cause",
                        {"cluster_id": cid_cluster, "week": data.get("week")},
                        question=question,
                    )
                    tools_used.extend(chain)
                    tool_results.append(("get_root_cause", rc))
                    break
        return tool_results

    def stream_tokens(self, answer: str):
        """Yield answer word-by-word for SSE."""
        words = answer.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    def _plan(self, question: str, history: list[dict], week: str | None) -> dict:
        settings = get_settings()
        if settings.openai_api_key:
            try:
                return self._plan_llm(question, history, week, settings.openai_api_key)
            except Exception as e:
                logger.warning("LLM plan failed, using router: %s", e)
        return self._plan_router(question, history, week)

    def _parse_limit(self, q: str, default: int = 3) -> int:
        m = re.search(r"(?:top|first)\s+(\d+)", q)
        if m:
            return min(int(m.group(1)), 10)
        return default

    def _score_keywords(self, q: str, keywords: tuple[str, ...], weight: int = 1) -> int:
        return sum(weight for kw in keywords if kw in q)

    def _resolve_context(self, question: str, history: list[dict]) -> tuple[str | None, str | None]:
        """Site/theme from current question, then recent user turns (follow-ups)."""
        q = question.lower()
        site_id = self._match_site(q)
        theme = self._match_theme(q)
        if site_id and theme:
            return site_id, theme
        for msg in reversed(history):
            if msg.get("role") != "user":
                continue
            prev = msg["content"].lower()
            site_id = site_id or self._match_site(prev)
            theme = theme or self._match_theme(prev)
            if site_id and theme:
                break
        return site_id, theme

    def _plan_router(self, question: str, history: list[dict], week: str | None) -> dict:
        q = question.lower().strip()
        w = week
        site_id, theme = self._resolve_context(question, history)
        limit = self._parse_limit(q)

        wants_verbatim = self._score_keywords(q, ("comment", "comments", "quote", "said", "verbatim", "guest said"))
        wants_negative = self._score_keywords(q, ("negative", "complaint", "worst", "bad review"))
        wants_positive = "positive" in q and wants_negative == 0
        wants_issues = self._score_keywords(q, ("top", "issue", "issues", "problem", "priority", "complaint", "flag"))
        wants_summary = self._score_keywords(q, ("summar", "leadership", "briefing", "overview", "status"))
        wants_compare = "compare" in q or " vs " in q or " versus " in q

        candidates: list[tuple[int, str, dict]] = []

        if (wants_negative or wants_verbatim) and not wants_positive:
            args: dict[str, Any] = {"week": w, "limit": limit}
            if site_id:
                args["site_id"] = site_id
            if theme:
                args["theme"] = theme
            candidates.append((wants_negative * 3 + wants_verbatim * 2 + 2, "get_negative_feedback", args))

        if self._score_keywords(q, ("sla", "breach", "on track", "at risk")):
            candidates.append((8, "get_sla_status", {"week": w}))

        if ("cross" in q and "source" in q) or "compounding" in q:
            kind = "compounding" if "compounding" in q else "cross_source"
            candidates.append((9, "get_detections", {"week": w, "kind": kind}))

        if self._score_keywords(q, ("root cause", "why is", "why are", "why")):
            if site_id:
                candidates.append((10, "get_site", {"site_id": site_id, "week": w}))
            else:
                candidates.append((6, "get_top_issues", {"week": w}))

        if self._score_keywords(q, ("language", "multilingual", "translated", "languages")):
            candidates.append((9, "get_language_mix", {"week": w}))

        if wants_positive:
            candidates.append((9, "get_positive_themes", {"week": w}))

        if self._score_keywords(q, ("trend", "over weeks", "week over week")) or (
            "weeks" in q and theme
        ):
            candidates.append((8, "get_theme_trend", {"theme": theme or "projection_quality"}))

        if wants_summary:
            candidates.append((7, "get_top_issues", {"week": w}))

        if wants_compare and site_id:
            other = "northgate" if site_id == "harbourview" else "harbourview"
            return {
                "tools": [
                    {"name": "get_site", "args": {"site_id": site_id, "week": w}},
                    {"name": "get_site", "args": {"site_id": other, "week": w}},
                ]
            }

        if wants_issues and not wants_verbatim and not wants_negative:
            candidates.append((wants_issues * 2 + 3, "get_top_issues", {"week": w}))

        if site_id and not candidates:
            candidates.append((5, "get_site", {"site_id": site_id, "week": w}))

        if self._score_keywords(q, ("search", "find", "mention", "contain")):
            candidates.append((6, "search_feedback", {"text": question, "week": w}))

        if theme and not candidates:
            candidates.append((4, "get_theme_trend", {"theme": theme}))

        if not candidates:
            candidates.append((1, "get_top_issues", {"week": w}))

        candidates.sort(key=lambda x: -x[0])
        best_score = candidates[0][0]
        top = [c for c in candidates if c[0] >= best_score - 1][:2]

        tools = [{"name": name, "args": args} for _, name, args in top]
        seen: set[str] = set()
        unique = []
        for t in tools:
            key = (t["name"], json.dumps(t["args"], sort_keys=True))
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return {"tools": unique}

    def _plan_llm(self, question: str, history: list[dict], week: str | None, api_key: str) -> dict:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        tool_specs = [
            {
                "name": k,
                "description": f"Retrieve {k}",
                "parameters": {"type": "object", "properties": {"week": {"type": "string"}}},
            }
            for k in RETRIEVAL_TOOLS
        ]
        msgs = [{"role": "system", "content": "Choose retrieval tools only. Week context: " + (week or "latest")}]
        msgs.extend(history[-6:])
        msgs.append({"role": "user", "content": question})
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=msgs,
            tools=[{"type": "function", "function": t} for t in tool_specs],
            tool_choice="auto",
        )
        tools = []
        msg = resp.choices[0].message
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                if week and "week" not in args:
                    args["week"] = week
                tools.append({"name": tc.function.name, "args": args})
        if not tools:
            return self._plan_router(question, history, week)
        return {"tools": tools}

    def _compose_answer(
        self, question: str, tool_results: list[tuple[str, dict]], week: str | None
    ) -> tuple[str, list[dict]]:
        references: list[dict] = []
        parts: list[str] = []

        for tool_name, data in tool_results:
            w = data.get("week") or week or "this week"

            if tool_name == "get_negative_feedback":
                items = data.get("items", [])
                if not items:
                    parts.append(f"No negative guest comments found for {w}.")
                else:
                    parts.append(f"Top {len(items)} negative comment(s) for {w}:")
                    for i, item in enumerate(items, 1):
                        snippet = item["text"][:140].rstrip()
                        if len(item["text"]) > 140:
                            snippet += "…"
                        parts.append(
                            f"{i}. {item['site_name']} ({item['theme'].replace('_', ' ')}, "
                            f"{item['channel']}): \"{snippet}\""
                        )
                        references.append({
                            "cluster_id": item.get("id", ""),
                            "site_id": item.get("site_id", ""),
                            "site_name": item.get("site_name", ""),
                            "theme": item.get("theme", ""),
                            "week": w,
                            "label": f"{item.get('site_name')} · {item.get('theme', '').replace('_', ' ')}",
                        })

            elif tool_name == "get_top_issues":
                ov = data.get("overview", {})
                q_lower = question.lower()
                ranked = ov.get("ranked_actions", [])
                is_summary = any(k in q_lower for k in ("summar", "leadership", "briefing", "overview"))

                if is_summary:
                    parts.append(
                        f"Week {w} leadership summary: {ov.get('items_processed', 0)} items processed, "
                        f"{ov.get('open_issues', 0)} open issues, "
                        f"{ov.get('cross_source_flags', 0)} cross-source flags, "
                        f"weighted CSAT {ov.get('weighted_csat_pct', 0)}%."
                    )
                if ranked:
                    n = self._parse_limit(q_lower, default=3)
                    parts.append(f"Top {min(n, len(ranked))} priority issue(s) for {w}:")
                    for i, r in enumerate(ranked[:n], 1):
                        parts.append(
                            f"{i}. {r['site_name']} — {r['theme'].replace('_', ' ')} "
                            f"({r.get('priority', 'P?')}, {r.get('neg', '?')} negatives)"
                        )
                        references.append({
                            "cluster_id": r["cluster_id"],
                            "site_id": r.get("site_id", ""),
                            "site_name": r.get("site_name", ""),
                            "theme": r.get("theme", ""),
                            "week": w,
                            "label": f"{r.get('site_name')} · {r.get('theme', '').replace('_', ' ')}",
                        })
                elif not is_summary:
                    hero = ov.get("hero_issue")
                    if hero:
                        parts.append(
                            f"Top priority: {hero['site_name']} — {hero['theme'].replace('_', ' ')} "
                            f"({hero['priority']}, {hero['neg']} negatives)."
                        )
                        references.append(self._ref(hero))
                    else:
                        parts.append(f"No open priority issues for {w}.")

            elif tool_name == "get_site":
                clusters = data.get("clusters", [])
                site_name = data.get("site_name", "Site")
                if not clusters:
                    parts.append(f"No negative clusters for {site_name} in {w}.")
                else:
                    site_blocks = [t for t in tool_results if t[0] == "get_site"]
                    if len(site_blocks) > 1:
                        top = clusters[0]
                        parts.append(
                            f"{site_name}: {top['theme'].replace('_', ' ')} "
                            f"({top['neg']} negatives"
                            + (f", {top['priority']}" if top.get("priority") else "")
                            + ")"
                        )
                    else:
                        top = clusters[0]
                        parts.append(f"{site_name} — top issues in {w}:")
                        for i, c in enumerate(clusters[:3], 1):
                            parts.append(
                                f"{i}. {c['theme'].replace('_', ' ')} — {c['neg']} negatives"
                                + (f" ({c['priority']})" if c.get("priority") else "")
                            )
                    references.append(self._ref_from_cluster(clusters[0], w))

            elif tool_name == "get_root_cause":
                if not data.get("found"):
                    parts.append("No root cause data for that cluster in the selected week.")
                else:
                    rc = data["root_cause"]
                    parts.append(
                        f"Root cause ({data.get('priority', 'P?')}): {rc.get('category')} — {rc.get('summary')}."
                    )
                    references.append({
                        "cluster_id": data["cluster_id"],
                        "site_id": "",
                        "site_name": "",
                        "theme": "",
                        "week": w,
                        "label": data["cluster_id"],
                    })

            elif tool_name == "get_detections":
                items = data.get("detections", [])
                if not items:
                    parts.append(f"No {data.get('kind') or ''} detections for {w}.")
                else:
                    desc = "; ".join(
                        f"{i['site_name']} {i['theme'].replace('_', ' ')} ({i.get('priority') or 'flagged'})"
                        for i in items[:3]
                    )
                    parts.append(f"Found {len(items)} detection(s): {desc}.")
                    for i in items[:3]:
                        references.append(self._ref_from_detection(i))

            elif tool_name == "get_sla_status":
                sm = data.get("summary", {})
                parts.append(
                    f"SLA summary for {w}: {sm.get('on_track', 0)} on track, "
                    f"{sm.get('at_risk', 0)} at risk, {sm.get('breached', 0)} breached."
                )
                for item in data.get("items", [])[:3]:
                    if item.get("sla_status") == "breached":
                        references.append(self._ref_from_sla_item(item, w))

            elif tool_name == "get_theme_trend":
                weeks = data.get("weeks", [])
                if weeks:
                    trend = ", ".join(f"{x['week']}: {x['neg']} neg" for x in weeks[-4:])
                    parts.append(f"{data.get('theme', 'theme')} trend: {trend}.")
                else:
                    parts.append(f"No trend data for theme {data.get('theme')}.")

            elif tool_name == "get_language_mix":
                langs = data.get("languages", [])
                if langs:
                    mix = ", ".join(f"{l['language']} ({l['count']})" for l in langs[:5])
                    parts.append(f"Language mix for {w}: {mix}.")
                else:
                    parts.append(f"No language stats for {w}.")

            elif tool_name == "get_positive_themes":
                themes = data.get("positive_themes", [])
                if themes:
                    t0 = themes[0]
                    parts.append(f"Strongest positive theme: {t0[0].replace('_', ' ')} with {t0[1]} mentions.")
                else:
                    parts.append("No positive theme data available.")

            elif tool_name == "search_feedback":
                matches = data.get("matches", [])
                if matches:
                    parts.append(f"Found {len(matches)} matching feedback item(s):")
                    for i, m in enumerate(matches[:3], 1):
                        parts.append(f"{i}. \"{m['text'][:120]}…\"")
                else:
                    parts.append(f"No feedback matching \"{data.get('query')}\" in {w}.")

        if not parts:
            return (
                "I don't have computed data covering that question. "
                "Try asking about top issues, negative comments, a site name, SLA status, or cross-source flags.",
                [],
            )
        return "\n".join(parts), references

    def _ref(self, hero: dict) -> dict:
        return {
            "cluster_id": hero["cluster_id"],
            "site_id": hero.get("site_id", ""),
            "site_name": hero.get("site_name", ""),
            "theme": hero.get("theme", ""),
            "week": hero.get("week", ""),
            "label": f"{hero.get('site_name')} · {hero.get('theme', '').replace('_', ' ')} · {hero.get('week', '')}",
        }

    def _ref_from_cluster(self, c: dict, week: str) -> dict:
        site = SITE_BY_ID.get(c.get("site_id", ""), {})
        return {
            "cluster_id": c["cluster_id"],
            "site_id": c.get("site_id", ""),
            "site_name": site.get("name", c.get("site_id", "")),
            "theme": c.get("theme", ""),
            "week": week,
            "label": f"{site.get('name', c.get('site_id'))} · {c.get('theme', '').replace('_', ' ')} · {week}",
        }

    def _ref_from_detection(self, d: dict) -> dict:
        return {
            "cluster_id": d["cluster_id"],
            "site_id": d.get("site_id", ""),
            "site_name": d.get("site_name", ""),
            "theme": d.get("theme", ""),
            "week": d.get("week", ""),
            "label": f"{d.get('site_name')} · {d.get('theme', '').replace('_', ' ')} · {d.get('week', '')}",
        }

    def _ref_from_sla_item(self, item: dict, week: str) -> dict:
        return {
            "cluster_id": item.get("cluster_id", ""),
            "site_id": item.get("site_id", ""),
            "site_name": SITE_BY_ID.get(item.get("site_id", ""), {}).get("name", ""),
            "theme": item.get("theme", ""),
            "week": week,
            "label": f"{item.get('cluster_id', 'issue')} · SLA {item.get('sla_status')}",
        }

    def _match_site(self, q: str) -> str | None:
        for site_id, site in SITE_BY_ID.items():
            if site_id in q or site["name"].lower() in q:
                return site_id
        return None

    def _match_theme(self, q: str) -> str | None:
        mapping = {
            "projection": "projection_quality",
            "audio": "audio_sound",
            "food": "f_and_b",
            "ticketing": "ticketing_queue",
            "queue": "ticketing_queue",
            "staff": "staff_service",
            "clean": "cleanliness",
        }
        for key, theme in mapping.items():
            if key in q:
                return theme
        return None
