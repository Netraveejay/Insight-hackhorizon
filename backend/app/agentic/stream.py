from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], None]


class RunStreamBus:
    """Live stream for triggers, reasoning steps, and run updates."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[EventCallback] = []

    def subscribe(self, callback: EventCallback) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def emit(self, payload: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(payload)
            except Exception as e:
                logger.warning("Run stream subscriber error: %s", e)

    async def stream_live(self):
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def on_event(payload: dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, payload)

        unsub = self.subscribe(on_event)
        try:
            while True:
                yield await queue.get()
        finally:
            unsub()


_bus: RunStreamBus | None = None


def get_run_stream() -> RunStreamBus:
    global _bus
    if _bus is None:
        _bus = RunStreamBus()
    return _bus
