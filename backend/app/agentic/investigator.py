"""InvestigatorAgent — auto-triggered on P1 / manual investigate."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agentic.loop import ReActLoop
from app.agentic.types import AgentRun, Trigger
from app.schemas import SITE_BY_ID


class InvestigatorAgent:
    def run(self, db: Session, trigger: Trigger) -> AgentRun:
        payload = trigger.payload
        cluster_id = payload.get("cluster_id", "")
        site_id = payload.get("site_id", "")
        theme = payload.get("theme", "")
        week = payload.get("week")
        site_name = SITE_BY_ID.get(site_id, {}).get("name", site_id) if site_id else cluster_id
        goal = (
            f"Explain P1 at {site_name} ({theme.replace('_', ' ') if theme else 'issue'}) "
            f"and assess severity and spread"
        )
        ctx = {
            "week": week,
            "cluster_id": cluster_id,
            "site_id": site_id,
            "theme": theme,
        }
        return ReActLoop().run(
            db,
            trigger=trigger,
            goal=goal,
            runner="investigator",
            context=ctx,
        )
