"""Application startup helpers."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.db import SessionLocal
from app.models import RunRow
from app.orchestrator import Orchestrator
from app.seed.generate import LATEST_WEEK

logger = logging.getLogger(__name__)


def ensure_seeded() -> None:
    """Load demo data on first boot when AUTO_SEED=true and DB is empty."""
    settings = get_settings()
    if not settings.auto_seed:
        return

    db = SessionLocal()
    try:
        if db.query(RunRow).count() > 0:
            return
        logger.info("Empty database — running initial seed pipeline for %s", LATEST_WEEK)
        from app.seed.generate import main as generate_main

        generate_main()
        Orchestrator(db).run_pipeline(week=LATEST_WEEK, cadence="bootstrap")
        logger.info("Bootstrap seed complete")
    except Exception as e:
        logger.error("Auto-seed failed: %s", e)
        db.rollback()
    finally:
        db.close()
