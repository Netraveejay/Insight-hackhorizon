from pathlib import Path

from fastapi import APIRouter

from app.routers import (
    agents,
    alerts,
    ask,
    auth,
    connectors,
    digest,
    feed,
    issues,
    languages,
    overview,
    pipeline,
    reports,
    rules,
    sites,
    trends,
)

api_router = APIRouter(prefix="/api")

for module in (
    overview,
    feed,
    issues,
    trends,
    digest,
    sites,
    alerts,
    rules,
    ask,
    agents,
    languages,
    pipeline,
    auth,
    reports,
    connectors,
):
    api_router.include_router(module.router)


def static_directory() -> Path | None:
    """Built frontend assets — checked in several locations for dev vs Docker."""
    candidates = [
        Path(__file__).resolve().parent.parent / "static",
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        Path("/app/static"),
    ]
    for path in candidates:
        if (path / "index.html").exists():
            return path
    return None
