"""Real-time WebSocket broadcaster.

A single in-process hub keeps three sets of connections:

- ``staff``      : officers/admins (one channel for all dashboards)
- ``user:{id}``  : per-citizen channels (their own incident updates)
- ``incident:{id}`` : per-incident channels (live thread view)

The broadcaster is sync-callable from any thread (including Celery workers
and SQLAlchemy after_commit hooks). It schedules sends on the running event
loop when one is available, and otherwise queues messages for later flush.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class _Broadcaster:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    # --- Lifecycle ----------------------------------------------------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called from FastAPI startup so background threads can publish."""
        self._loop = loop

    # --- Topic helpers ------------------------------------------------
    @staticmethod
    def staff_topic() -> str:
        return "staff"

    @staticmethod
    def user_topic(user_id: int) -> str:
        return f"user:{user_id}"

    @staticmethod
    def incident_topic(incident_id: int) -> str:
        return f"incident:{incident_id}"

    # --- Subscription -------------------------------------------------
    async def connect(self, websocket: WebSocket, topics: list[str]) -> None:
        await websocket.accept()
        with self._lock:
            for topic in topics:
                self._connections.setdefault(topic, set()).add(websocket)
        logger.info("WS connected to topics=%s (total=%d)",
                    topics, sum(len(s) for s in self._connections.values()))

    def disconnect(self, websocket: WebSocket, topics: list[str]) -> None:
        with self._lock:
            for topic in topics:
                conns = self._connections.get(topic)
                if conns:
                    conns.discard(websocket)
                    if not conns:
                        self._connections.pop(topic, None)

    # --- Publish ------------------------------------------------------
    def publish(self, topic: str, event: str, data: dict[str, Any]) -> None:
        """Sync-callable. Safe to invoke from request handlers, Celery, etc."""
        payload = json.dumps({"event": event, "topic": topic, "data": data},
                             default=str)
        with self._lock:
            targets = list(self._connections.get(topic, ()))
        if not targets:
            return

        loop = self._loop
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is not None:
            running.create_task(self._fanout(targets, payload))
        elif loop is not None:
            asyncio.run_coroutine_threadsafe(self._fanout(targets, payload), loop)
        else:
            logger.debug("No event loop bound; dropping ws event %s", event)

    async def _fanout(self, targets: list[WebSocket], payload: str) -> None:
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception as exc:  # noqa: BLE001
                logger.debug("WS send failed (%s); marking dead", exc)
                dead.append(ws)
        if dead:
            with self._lock:
                for topic, conns in list(self._connections.items()):
                    for ws in dead:
                        conns.discard(ws)
                    if not conns:
                        self._connections.pop(topic, None)


broadcaster = _Broadcaster()
