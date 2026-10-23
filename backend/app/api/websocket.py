from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # mission_id -> list of connected WebSockets
        self.active_mission_connections: Dict[str, List[WebSocket]] = {}
        self.active_stream_connections: Dict[str, List[WebSocket]] = {}

    async def connect_mission(self, websocket: WebSocket, mission_id: str):
        await websocket.accept()
        if mission_id not in self.active_mission_connections:
            self.active_mission_connections[mission_id] = []
        self.active_mission_connections[mission_id].append(websocket)

    def disconnect_mission(self, websocket: WebSocket, mission_id: str):
        if mission_id in self.active_mission_connections:
            if websocket in self.active_mission_connections[mission_id]:
                self.active_mission_connections[mission_id].remove(websocket)

    async def connect_stream(self, websocket: WebSocket, mission_id: str):
        await websocket.accept()
        if mission_id not in self.active_stream_connections:
            self.active_stream_connections[mission_id] = []
        self.active_stream_connections[mission_id].append(websocket)

    def disconnect_stream(self, websocket: WebSocket, mission_id: str):
        if mission_id in self.active_stream_connections:
            if websocket in self.active_stream_connections[mission_id]:
                self.active_stream_connections[mission_id].remove(websocket)

    async def broadcast_event(self, mission_id: str, event_data: Dict[str, Any]):
        if mission_id in self.active_mission_connections:
            dead_connections = []
            for ws in self.active_mission_connections[mission_id]:
                try:
                    await ws.send_json(event_data)
                except Exception:
                    dead_connections.append(ws)
            for d in dead_connections:
                self.disconnect_mission(d, mission_id)

    async def broadcast_frame(self, mission_id: str, base64_image: str):
        if mission_id in self.active_stream_connections:
            dead_connections = []
            msg = {"type": "screencast_frame", "mission_id": mission_id, "data": base64_image}
            for ws in self.active_stream_connections[mission_id]:
                try:
                    await ws.send_json(msg)
                except Exception:
                    dead_connections.append(ws)
            for d in dead_connections:
                self.disconnect_stream(d, mission_id)

manager = ConnectionManager()
