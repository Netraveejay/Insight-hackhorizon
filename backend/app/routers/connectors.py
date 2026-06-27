from fastapi import APIRouter

from app.config import get_settings
from app.connectors.registry import connector_catalog, load_connectors

router = APIRouter(tags=["connectors"])


@router.get("/connectors")
def list_connectors():
    settings = get_settings()
    active = load_connectors()
    return {
        "mode": "file" if active and active[0].name == "file" else "seed",
        "teams_webhook_configured": bool(settings.teams_webhook_url),
        "connectors": connector_catalog(),
    }
