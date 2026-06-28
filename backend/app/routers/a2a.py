from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.a2a.bus import get_bus
from app.a2a.registry import AGENT_REGISTRY, PIPELINE_EDGES, list_agents
from app.a2a.types import A2AMessage
from app.db import SessionLocal, get_db
from app.models import AgentMessageRow
from app.orchestrator import Orchestrator

router = APIRouter(tags=["a2a"])


@router.get("/agents")
def agent_registry():
    return {
        "agents": [a.model_dump() for a in list_agents()],
        "edges": [{"from": a, "to": b} for a, b in PIPELINE_EDGES],
    }


@router.get("/a2a/messages")
def list_messages(
    correlation_id: str = Query(...),
    limit: int = Query(200, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AgentMessageRow)
        .filter(AgentMessageRow.correlation_id == correlation_id)
        .order_by(AgentMessageRow.ts)
        .limit(limit)
        .all()
    )
    return {
        "correlation_id": correlation_id,
        "messages": [_row_to_msg(r).model_dump(mode="json") for r in rows],
    }


@router.get("/a2a/correlations")
def list_correlations(limit: int = 20, db: Session = Depends(get_db)):
    rows = (
        db.query(AgentMessageRow.correlation_id, AgentMessageRow.ts)
        .distinct()
        .order_by(desc(AgentMessageRow.ts))
        .limit(limit)
        .all()
    )
    seen: list[str] = []
    for cid, _ in rows:
        if cid not in seen:
            seen.append(cid)
    return {"correlation_ids": seen[:limit]}


@router.post("/a2a/run")
def run_pipeline_a2a(week: str | None = None):
    db = SessionLocal()
    try:
        result = Orchestrator(db).run_pipeline(week=week, cadence="manual")
        return result.model_dump()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        db.close()


@router.get("/a2a/stream")
async def stream_sse():
    """SSE fallback for live A2A messages."""

    async def event_gen():
        bus = get_bus()
        async for msg in bus.stream_live():
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.websocket("/a2a/ws")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    bus = get_bus()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_message(payload: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, payload)

    unsub = bus.subscribe(on_message)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        unsub()


def _row_to_msg(row: AgentMessageRow) -> A2AMessage:
    return A2AMessage(
        id=row.id,
        ts=row.ts,
        correlation_id=row.correlation_id,
        from_agent=row.from_agent,
        to_agent=row.to_agent,
        intent=row.intent,  # type: ignore[arg-type]
        summary=row.summary,
        status=row.status,  # type: ignore[arg-type]
        payload_ref=row.payload_ref,
    )
