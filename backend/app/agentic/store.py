from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agentic.stream import get_run_stream
from app.agentic.types import AgentRun, ReasoningStep, Trigger
from app.models import AgentRunRow, ReasoningStepRow, TriggerRow


def _step_id() -> str:
    return str(uuid.uuid4())[:12]


def save_trigger(db: Session, trigger: Trigger, *, commit: bool = False) -> None:
    row = TriggerRow(
        id=trigger.id,
        type=trigger.type,
        source=trigger.source,
        summary=trigger.summary,
        ts=trigger.ts,
        payload=trigger.payload,
    )
    db.add(row)
    if commit:
        db.commit()
    else:
        db.flush()
    get_run_stream().emit({"type": "trigger", "trigger": trigger.model_dump(mode="json")})


def create_run(db: Session, trigger: Trigger, goal: str, runner: str, *, commit: bool = False) -> AgentRun:
    save_trigger(db, trigger, commit=False)
    run_id = str(uuid.uuid4())[:12]
    started = datetime.utcnow()
    row = AgentRunRow(
        id=run_id,
        trigger_id=trigger.id,
        goal=goal,
        runner=runner,
        status="running",
        outcome=None,
        started_at=started,
        ended_at=None,
    )
    db.add(row)
    if commit:
        db.commit()
    else:
        db.flush()
    run = AgentRun(
        id=run_id,
        trigger=trigger,
        goal=goal,
        runner=runner,
        status="running",
        steps=[],
        outcome=None,
        started_at=started,
        ended_at=None,
    )
    get_run_stream().emit({"type": "run_start", "run": _run_dict(run)})
    return run


def append_step(db: Session, run: AgentRun, step: ReasoningStep, *, commit: bool = False) -> None:
    row = ReasoningStepRow(
        id=_step_id(),
        run_id=run.id,
        step_no=step.step_no,
        agent=step.agent,
        phase=step.phase,
        thought=step.thought,
        action=step.action,
        observation=step.observation,
        ts=step.ts,
    )
    db.add(row)
    run.steps.append(step)
    if commit:
        db.commit()
    else:
        db.flush()
    get_run_stream().emit({
        "type": "step",
        "run_id": run.id,
        "correlation_id": run.id,
        "step": step.model_dump(mode="json"),
    })


def complete_run(
    db: Session,
    run: AgentRun,
    outcome: str,
    status: str = "done",
    *,
    commit: bool = False,
) -> None:
    ended = datetime.utcnow()
    row = db.query(AgentRunRow).filter(AgentRunRow.id == run.id).first()
    if row:
        row.status = status
        row.outcome = outcome
        row.ended_at = ended
    run.status = status  # type: ignore[assignment]
    run.outcome = outcome
    run.ended_at = ended
    if commit:
        db.commit()
    else:
        db.flush()
    get_run_stream().emit({"type": "run_complete", "run": _run_dict(run)})


def load_run(db: Session, run_id: str) -> AgentRun | None:
    row = db.query(AgentRunRow).filter(AgentRunRow.id == run_id).first()
    if not row:
        return None
    trig_row = db.query(TriggerRow).filter(TriggerRow.id == row.trigger_id).first()
    if not trig_row:
        return None
    steps = (
        db.query(ReasoningStepRow)
        .filter(ReasoningStepRow.run_id == run_id)
        .order_by(ReasoningStepRow.step_no)
        .all()
    )
    trigger = Trigger(
        id=trig_row.id,
        type=trig_row.type,  # type: ignore[arg-type]
        source=trig_row.source,
        summary=trig_row.summary,
        ts=trig_row.ts,
        payload=trig_row.payload or {},
    )
    return AgentRun(
        id=row.id,
        trigger=trigger,
        goal=row.goal,
        runner=row.runner,
        status=row.status,  # type: ignore[arg-type]
        steps=[
            ReasoningStep(
                run_id=s.run_id,
                step_no=s.step_no,
                agent=s.agent,
                phase=s.phase,  # type: ignore[arg-type]
                thought=s.thought,
                action=s.action,
                observation=s.observation,
                ts=s.ts,
            )
            for s in steps
        ],
        outcome=row.outcome,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def list_runs(db: Session, limit: int = 30) -> list[dict[str, Any]]:
    rows = db.query(AgentRunRow).order_by(desc(AgentRunRow.started_at)).limit(limit).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        trig = db.query(TriggerRow).filter(TriggerRow.id == row.trigger_id).first()
        out.append({
            "id": row.id,
            "goal": row.goal,
            "runner": row.runner,
            "status": row.status,
            "outcome": row.outcome,
            "started_at": row.started_at.isoformat() + "Z",
            "ended_at": row.ended_at.isoformat() + "Z" if row.ended_at else None,
            "trigger": {
                "id": trig.id,
                "type": trig.type,
                "source": trig.source,
                "summary": trig.summary,
                "ts": trig.ts.isoformat() + "Z",
                "payload": trig.payload or {},
            }
            if trig
            else None,
        })
    return out


def _run_dict(run: AgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "correlation_id": run.id,
        "goal": run.goal,
        "runner": run.runner,
        "status": run.status,
        "outcome": run.outcome,
        "started_at": run.started_at.isoformat() + "Z",
        "ended_at": run.ended_at.isoformat() + "Z" if run.ended_at else None,
        "trigger": run.trigger.model_dump(mode="json"),
        "steps": [s.model_dump(mode="json") for s in run.steps],
    }


def summarize_observation(tool: str, result: dict) -> str:
    """Short grounded summary for observe steps — never invent."""
    try:
        if tool == "get_cluster":
            c = result.get("cluster") or {}
            return f"Cluster {result.get('cluster_id')}: {c.get('neg', 0)} negatives, volume {c.get('volume', 0)}"
        if tool == "get_root_cause":
            if not result.get("found"):
                return "No root cause taxonomy match"
            rc = result.get("root_cause", {})
            return f"{rc.get('category')}: {rc.get('summary', '')[:120]}"
        if tool == "check_contagion":
            return (
                f"{result.get('site_count', 0)} site(s) with {result.get('theme', 'theme')} issues; "
                f"spreading={result.get('spreading', False)}"
            )
        if tool == "correlate_with_staff":
            return (
                f"Guest negatives: {result.get('guest_neg', 0)}, staff signals: {result.get('staff_neg', 0)}, "
                f"cross_source={result.get('cross_source', False)}"
            )
        if tool == "compare_sites":
            return f"Compared {result.get('site_a', {}).get('site_name')} vs {result.get('site_b', {}).get('site_name')}"
        if tool == "get_negative_feedback":
            return f"{result.get('count', 0)} negative comment(s) retrieved"
        if tool == "get_top_issues":
            ov = result.get("overview", {})
            return f"{ov.get('open_issues', 0)} open issues, hero: {ov.get('hero_issue', {}).get('site_name', 'n/a')}"
        if tool == "get_sla_status":
            sm = result.get("summary", {})
            return f"SLA: {sm.get('on_track', 0)} on track, {sm.get('breached', 0)} breached"
        if tool == "get_detections":
            return f"{result.get('count', 0)} detection(s)"
        if tool == "get_site":
            return f"{result.get('site_name')}: {len(result.get('clusters', []))} cluster(s)"
        if tool == "get_theme_trend":
            return f"{len(result.get('weeks', []))} week(s) of trend data"
        if tool == "get_language_mix":
            return f"{len(result.get('languages', []))} language(s)"
        if tool == "search_feedback":
            return f"{result.get('count', 0)} matching feedback item(s)"
        return json.dumps(result)[:160]
    except Exception:
        return str(result)[:160]
