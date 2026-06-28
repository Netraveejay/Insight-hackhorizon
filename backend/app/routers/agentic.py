from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agentic.coordinator import CoordinatorAgent
from app.agentic.conversational import ConversationalAgent
from app.agentic.store import list_runs, load_run
from app.agentic.stream import get_run_stream
from app.db import SessionLocal, get_db

router = APIRouter(tags=["agentic"])


class InvestigateRequest(BaseModel):
    cluster_id: str
    week: str | None = None


class PipelineRunRequest(BaseModel):
    week: str | None = None


@router.get("/runs")
def get_runs(limit: int = 30, db: Session = Depends(get_db)):
    return {"runs": list_runs(db, limit=limit)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = load_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
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


@router.post("/runs/investigate")
def investigate(body: InvestigateRequest, db: Session = Depends(get_db)):
    try:
        run_id = CoordinatorAgent().manual_investigate(db, body.cluster_id, body.week)
        db.commit()
        run = load_run(db, run_id)
        return {"run_id": run_id, "run": run.model_dump(mode="json") if run else None}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/runs/pipeline")
def run_pipeline_agentic(body: PipelineRunRequest, db: Session = Depends(get_db)):
    try:
        result = CoordinatorAgent().run_full_pipeline(db, body.week, cadence="manual")
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/runs/stream/sse")
async def runs_stream_sse():
    async def gen():
        bus = get_run_stream()
        async for event in bus.stream_live():
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.websocket("/runs/stream")
async def runs_stream_ws(websocket: WebSocket):
    await websocket.accept()
    bus = get_run_stream()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_event(payload: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, payload)

    unsub = bus.subscribe(on_event)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        unsub()
