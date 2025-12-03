from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.room_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.dashboard_connections: Set[WebSocket] = set()
        self.lobby_connections: Dict[WebSocket, dict[str, str]] = {}

    async def connect_room(self, room_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.room_connections[room_id].add(websocket)

    def disconnect_room(self, room_id: str, websocket: WebSocket) -> None:
        if room_id in self.room_connections:
            self.room_connections[room_id].discard(websocket)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]

    async def broadcast_room(self, room_id: str, payload: dict) -> None:
        connections = self.room_connections.get(room_id, set()).copy()
        for connection in connections:
            await connection.send_json(payload)

    async def connect_dashboard(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.dashboard_connections.add(websocket)

    def disconnect_dashboard(self, websocket: WebSocket) -> None:
        self.dashboard_connections.discard(websocket)

    async def broadcast_dashboard(self, payload: dict) -> None:
        connections = self.dashboard_connections.copy()
        for connection in connections:
            await connection.send_json(payload)

    async def connect_lobby(self, websocket: WebSocket, user_info: dict[str, str]) -> None:
        await websocket.accept()
        self.lobby_connections[websocket] = {
            "user_id": user_info.get("user_id", ""),
            "username": user_info.get("username", "Guest"),
        }

    def disconnect_lobby(self, websocket: WebSocket) -> None:
        self.lobby_connections.pop(websocket, None)

    async def broadcast_lobby(self, payload: dict) -> None:
        connections = list(self.lobby_connections.keys())
        for connection in connections:
            await connection.send_json(payload)

    @property
    def online_player_count(self) -> int:
        return sum(len(conns) for conns in self.room_connections.values())

    @property
    def lobby_roster(self) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        # iterate in reverse so the most recent connection for a user wins
        for data in reversed(list(self.lobby_connections.values())):
            user_id = data.get("user_id", "")
            username = data.get("username", "Guest")
            if not user_id or user_id in seen:
                continue
            seen.add(user_id)
            deduped.append({"user_id": user_id, "username": username})
        deduped.reverse()
        return deduped


manager = ConnectionManager()

