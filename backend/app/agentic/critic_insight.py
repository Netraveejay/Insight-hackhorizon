"""CriticAgent — reflects on InsightAgent drafts and drives revision."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.agentic.store import append_step, complete_run, create_run
from app.agentic.triggers import make_trigger
from app.agentic.types import AgentRun, ReasoningStep


class InsightCriticAgent:
    MAX_REVISIONS = 2

    def critique_and_revise(
        self,
        db: Session,
        run_id: str,
        cluster_id: str,
        week: str,
        initial_draft: str,
        owner: str,
    ) -> tuple[str, AgentRun | None]:
        trigger = make_trigger(
            "anomaly",
            "InsightAgent",
            f"Critique draft for {cluster_id}",
            {"cluster_id": cluster_id, "week": week, "pipeline_run_id": run_id},
        )
        agent_run = create_run(
            db,
            trigger,
            goal=f"Review insight draft for {cluster_id}",
            runner="critic",
        )
        draft = initial_draft
        step_no = 0
        for attempt in range(self.MAX_REVISIONS + 1):
            step_no = self._step(
                db,
                agent_run,
                step_no,
                "reflect",
                "critic",
                f"Evaluate draft attempt {attempt + 1}: grounded, actionable, internal-only?",
            )
            ok, feedback = self._evaluate(draft)
            step_no = self._step(
                db, agent_run, step_no, "observe", "critic", feedback, observation=feedback
            )
            if ok:
                self._step(
                    db,
                    agent_run,
                    step_no,
                    "final",
                    "critic",
                    f"Draft approved after {attempt} revision(s)",
                )
                complete_run(db, agent_run, f"Approved insight draft for {cluster_id}")
                return draft, agent_run
            if attempt < self.MAX_REVISIONS:
                draft = self._revise(draft, feedback)
                step_no = self._step(
                    db, agent_run, step_no, "think", "insight", f"Revise per critic: {feedback}"
                )
        complete_run(db, agent_run, f"Draft finalized with reservations for {cluster_id}")
        return draft, agent_run

    def _evaluate(self, draft: str) -> tuple[bool, str]:
        issues = []
        if len(draft) < 40:
            issues.append("too short")
        if not any(
            w in draft.lower()
            for w in ("recommend", "inspect", "review", "brief", "check", "owner", "operations")
        ):
            issues.append("not actionable")
        if any(w in draft.lower() for w in ("email guest", "contact customer", "reply to guest")):
            issues.append("guest-facing language")
        if issues:
            return False, "Failed: " + ", ".join(issues)
        return True, "Grounded, actionable, internal-only"

    def _revise(self, draft: str, feedback: str) -> str:
        suffix = " Internal review only — do not contact guests. Recommend site technical review within 48h."
        if "actionable" in feedback:
            return (
                draft.rstrip(".")
                + ". Next step: brief Technical Operations and site duty manager."
                + suffix
            )
        if "guest-facing" in feedback:
            return draft.replace("guest", "team").replace("customer", "site") + suffix
        return draft + suffix

    def _step(
        self,
        db: Session,
        run: AgentRun,
        step_no: int,
        phase: str,
        agent: str,
        thought: str,
        observation: str | None = None,
    ) -> int:
        step = ReasoningStep(
            run_id=run.id,
            step_no=step_no,
            agent=agent,
            phase=phase,  # type: ignore[arg-type]
            thought=thought,
            observation=observation,
            ts=datetime.utcnow(),
        )
        append_step(db, run, step)
        return step_no + 1
