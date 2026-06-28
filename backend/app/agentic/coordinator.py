"""CoordinatorAgent — pipeline triggers and P1 branching."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agentic.investigator import InvestigatorAgent
from app.agentic.store import save_trigger
from app.agentic.triggers import make_trigger
from app.agentic.types import Trigger
from app.models import ClusterRow, DetectionRow
from app.schemas import SITE_BY_ID


class CoordinatorAgent:
    def run_full_pipeline(self, db: Session, week: str | None, cadence: str = "manual") -> dict:
        trigger = make_trigger(
            "schedule" if cadence == "scheduled" else "manual",
            "CoordinatorAgent",
            f"Pipeline run for week {week or 'latest'}",
            {"week": week, "action": "pipeline", "cadence": cadence},
        )
        save_trigger(db, trigger)
        from app.orchestrator import Orchestrator

        result = Orchestrator(db).run_pipeline(week=week, cadence=cadence)
        db.commit()
        return result.model_dump()

    def investigate_p1s_for_run(self, db: Session, run_id: str) -> list[str]:
        return self._spawn_p1_investigations(db, run_id)

    def _spawn_p1_investigations(self, db: Session, run_id: str) -> list[str]:
        run_ids: list[str] = []
        p1_rows = (
            db.query(DetectionRow)
            .filter(DetectionRow.run_id == run_id, DetectionRow.priority == "P1")
            .all()
        )
        for det in p1_rows:
            cluster = db.query(ClusterRow).filter(ClusterRow.cluster_id == det.cluster_id).first()
            if not cluster:
                continue
            site_name = SITE_BY_ID.get(cluster.site_id, {}).get("name", cluster.site_id)
            trigger = make_trigger(
                "detection",
                "DetectionAgent",
                f"P1 detected: {site_name} / {cluster.theme.replace('_', ' ')}",
                {
                    "cluster_id": cluster.cluster_id,
                    "site_id": cluster.site_id,
                    "theme": cluster.theme,
                    "week": cluster.week,
                    "priority": "P1",
                },
            )
            inv_run = InvestigatorAgent().run(db, trigger)
            run_ids.append(inv_run.id)
        return run_ids

    def manual_investigate(self, db: Session, cluster_id: str, week: str | None = None) -> str:
        cluster = db.query(ClusterRow).filter(ClusterRow.cluster_id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster not found: {cluster_id}")
        site_name = SITE_BY_ID.get(cluster.site_id, {}).get("name", cluster.site_id)
        trigger = make_trigger(
            "manual",
            "user",
            f"Manual investigate: {site_name} / {cluster.theme.replace('_', ' ')}",
            {
                "cluster_id": cluster.cluster_id,
                "site_id": cluster.site_id,
                "theme": cluster.theme,
                "week": week or cluster.week,
            },
        )
        run = InvestigatorAgent().run(db, trigger)
        return run.id
