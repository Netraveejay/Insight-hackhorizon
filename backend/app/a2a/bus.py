from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.a2a.types import A2AMessage
from app.models import AgentMessageRow

logger = logging.getLogger(__name__)

MessageCallback = Callable[[dict[str, Any]], None]


class A2ABus:
    """In-process pub/sub — swappable for Redis/NATS later."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[MessageCallback] = []

    def subscribe(self, callback: MessageCallback) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def _notify(self, payload: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(payload)
            except Exception as e:
                logger.warning("A2A subscriber error: %s", e)

    def send(
        self,
        db: Session,
        *,
        correlation_id: str,
        from_agent: str,
        to_agent: str,
        intent: str,
        summary: str,
        status: str = "sent",
        payload_ref: str | None = None,
        ts: datetime | None = None,
        commit: bool = False,
    ) -> A2AMessage:
        msg = A2AMessage(
            id=str(uuid.uuid4())[:12],
            ts=ts or datetime.utcnow(),
            correlation_id=correlation_id,
            from_agent=from_agent,
            to_agent=to_agent,
            intent=intent,  # type: ignore[arg-type]
            summary=summary,
            status=status,  # type: ignore[arg-type]
            payload_ref=payload_ref,
        )
        row = AgentMessageRow(
            id=msg.id,
            ts=msg.ts,
            correlation_id=msg.correlation_id,
            from_agent=msg.from_agent,
            to_agent=msg.to_agent,
            intent=msg.intent,
            summary=msg.summary,
            status=msg.status,
            payload_ref=msg.payload_ref,
        )
        db.add(row)
        if commit:
            db.commit()
        else:
            db.flush()
        payload = msg.model_dump(mode="json")
        if isinstance(payload.get("ts"), datetime):
            payload["ts"] = payload["ts"].isoformat() + "Z"
        self._notify(payload)
        return msg

    async def stream_live(self):
        """Async generator for WebSocket clients."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def on_message(payload: dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, payload)

        unsub = self.subscribe(on_message)
        try:
            while True:
                yield await queue.get()
        finally:
            unsub()


_bus: A2ABus | None = None


def get_bus() -> A2ABus:
    global _bus
    if _bus is None:
        _bus = A2ABus()
    return _bus
