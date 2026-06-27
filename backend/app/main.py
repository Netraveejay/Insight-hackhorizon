import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.orchestrator import Orchestrator
from app.startup import ensure_seeded
from app.static_files import api_router, static_directory

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _scheduled_pipeline(cadence: str):
    db = SessionLocal()
    try:
        Orchestrator(db).run_pipeline(cadence=cadence)
    except Exception as e:
        logger.error("Scheduled pipeline failed: %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_seeded()
    settings = get_settings()

    if settings.enable_scheduler:
        scheduler.add_job(_scheduled_pipeline, "interval", minutes=30, id="ingest", kwargs={"cadence": "continuous"})
        scheduler.add_job(
            _scheduled_pipeline, "cron", day_of_week="mon", hour=7, minute=0, id="weekly_digest", kwargs={"cadence": "weekly"}
        )
        scheduler.add_job(
            _scheduled_pipeline, "cron", day="last", hour=18, minute=0, id="monthly_summary", kwargs={"cadence": "monthly"}
        )
        scheduler.start()
        logger.info("Insight API started — scheduler active")
    else:
        logger.info("Insight API started — scheduler disabled")

    static = static_directory()
    if static:
        logger.info("Serving frontend from %s", static)
    yield
    if settings.enable_scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Insight — Guest Feedback Intelligence",
    description="Multi-site cinema feedback intelligence (inform, not act)",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
@app.get("/health")
def health():
    static = static_directory()
    return {
        "status": "ok",
        "service": "insight",
        "version": "1.0.0",
        "frontend": static is not None,
    }


# ── Production: serve React SPA (must be after API routes) ───────────────────
_static = static_directory()
if _static:

    @app.get("/")
    async def spa_root():
        return FileResponse(_static / "index.html")

    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """React Router paths — return index.html unless a static file exists."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = _static / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
