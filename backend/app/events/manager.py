from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.room_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.dashboard_connections: Set[WebSocket] = set()

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

    @property
    def online_player_count(self) -> int:
        return sum(len(conns) for conns in self.room_connections.values())


manager = ConnectionManager()

