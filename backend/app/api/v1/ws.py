"""WebSocket endpoints.

Clients authenticate by passing a JWT access token as the ``token`` query
parameter (browsers cannot set custom headers on WebSocket connections).

Routes:

- ``/ws/staff``           : officers + admins receive every new/changed incident.
- ``/ws/citizen``         : a citizen receives updates for their own incidents.
- ``/ws/incidents/{id}``  : live thread for one incident (anyone allowed to view it).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.database import session_scope
from app.models.incident import Incident
from app.models.user import User, UserRole
from app.realtime import broadcaster

router = APIRouter()
logger = logging.getLogger(__name__)


def _authenticate(token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    with session_scope() as db:
        user = db.get(User, int(user_id))
        if user and user.is_active:
            db.expunge(user)
            return user
    return None


@router.websocket("/staff")
async def staff_stream(websocket: WebSocket, token: str | None = Query(default=None)):
    user = _authenticate(token)
    if not user or user.role not in (UserRole.officer, UserRole.admin):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    topics = [broadcaster.staff_topic()]
    await broadcaster.connect(websocket, topics)
    try:
        while True:
            # Drain client pings; we don't expect application messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.disconnect(websocket, topics)


@router.websocket("/citizen")
async def citizen_stream(websocket: WebSocket, token: str | None = Query(default=None)):
    user = _authenticate(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    topics = [broadcaster.user_topic(user.id)]
    await broadcaster.connect(websocket, topics)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.disconnect(websocket, topics)


@router.websocket("/incidents/{incident_id}")
async def incident_stream(
    websocket: WebSocket,
    incident_id: int,
    token: str | None = Query(default=None),
):
    user = _authenticate(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    with session_scope() as db:
        incident = db.get(Incident, incident_id)
        if not incident:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        allowed = (
            user.role in (UserRole.officer, UserRole.admin)
            or incident.reporter_id == user.id
        )
    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    topics = [broadcaster.incident_topic(incident_id)]
    await broadcaster.connect(websocket, topics)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.disconnect(websocket, topics)
