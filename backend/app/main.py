import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator
import json

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db, async_session_factory
from .events.manager import manager
from .models import User
from .routers import auth, users, rooms, tournaments, dashboard, admin, special_game
from .security import decode_token
from .services.room_cleanup import delete_idle_rooms

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    cleanup_task = asyncio.create_task(_room_cleanup_loop())
    yield
    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(users.router, prefix=settings.api_prefix)
    app.include_router(rooms.router, prefix=settings.api_prefix)
    app.include_router(tournaments.router, prefix=settings.api_prefix)
    app.include_router(dashboard.router, prefix=settings.api_prefix)
    app.include_router(admin.router, prefix=settings.api_prefix)
    app.include_router(special_game.router, prefix=settings.api_prefix)

    @app.get("/healthz")
    async def healthcheck():
        return {"status": "ok"}

    @app.websocket("/ws/rooms/{room_id}")
    async def room_socket(websocket: WebSocket, room_id: str):
        await manager.connect_room(room_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect_room(room_id, websocket)

    @app.websocket("/ws/dashboard")
    async def dashboard_socket(websocket: WebSocket):
        await manager.connect_dashboard(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect_dashboard(websocket)

    @app.websocket("/ws/lobby")
    async def lobby_socket(websocket: WebSocket, token: str | None = Query(default=None)):
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        try:
            decoded = decode_token(token)
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = decoded.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        async with async_session_factory() as session:
            user = await session.get(User, user_id)

        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect_lobby(websocket, {"user_id": user.id, "username": user.username})
        await manager.broadcast_lobby({"type": "roster", "users": manager.lobby_roster})
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") != "chat":
                    continue
                message = (payload.get("message") or "").strip()
                if not message:
                    continue
                sanitized = message[:500]
                client_id = payload.get("client_id")
                await manager.broadcast_lobby(
                    {
                        "type": "chat",
                        "user": user.username,
                        "user_id": user.id,
                        "message": sanitized,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "client_id": client_id,
                    }
                )
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect_lobby(websocket)
            await manager.broadcast_lobby({"type": "roster", "users": manager.lobby_roster})

    return app


async def _room_cleanup_loop() -> None:
    interval = max(60, settings.room_cleanup_interval_seconds)
    try:
        while True:
            await asyncio.sleep(interval)
            cutoff = datetime.utcnow() - timedelta(minutes=max(5, settings.room_idle_minutes))
            try:
                async with async_session_factory() as session:
                    deleted = await delete_idle_rooms(session, cutoff=cutoff, reason="idle_cleanup")
                    if deleted:
                        logger.info("Removed %s idle rooms", deleted)
            except Exception:  # noqa: BLE001
                logger.exception("Room cleanup loop failed")
    except asyncio.CancelledError:
        logger.debug("Room cleanup loop cancelled")
        raise


app = create_app()

