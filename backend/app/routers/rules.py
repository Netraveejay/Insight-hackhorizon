from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.orchestrator import Orchestrator
from app.rules import apply_rescore_overrides, load_rules, save_rules
from app.schemas import RulesRescoreRequest

router = APIRouter(tags=["rules"])


@router.get("/rules")
def get_rules():
    config = load_rules()
    return config.model_dump()


@router.post("/rules/rescore")
def rescore(body: RulesRescoreRequest, db: Session = Depends(get_db)):
    current = load_rules()
    overrides = body.model_dump(exclude_none=True)
    new_config = apply_rescore_overrides(current, overrides)
    save_rules(new_config)
    from app.seed.generate import LATEST_WEEK

    result = Orchestrator(db).run_pipeline(week=LATEST_WEEK, cadence="rescore")
    return {
        "rules_version": new_config.version,
        "config": new_config.model_dump(),
        "pipeline": result.model_dump(),
        "message": "Re-scored with no rebuild — new rules_version stamped on all items",
    }
