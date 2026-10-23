import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os

from app.config import settings
from app.database.db import init_db, Database
from app.api.routes import api_router
from app.demo_site.server import demo_router
from app.api.websocket import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and Artifacts directory
    init_db()
    settings.absolute_artifacts_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown

app = FastAPI(
    title="VECTOR — Autonomous Web Operator",
    description="Full-stack autonomous browser automation, API routing, DOM inspection, and verified execution system.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware configured for Vercel, Render, and Localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST Routers
app.include_router(api_router)
app.include_router(demo_router)

@app.websocket("/ws/missions/{mission_id}")
async def websocket_mission_events(websocket: WebSocket, mission_id: str):
    await manager.connect_mission(websocket, mission_id)
    try:
        # Replay past events to newly connected client to eliminate race conditions
        past_events = Database.get_events(mission_id)
        for ev in past_events:
            try:
                await websocket.send_json(ev)
            except Exception:
                break
    except Exception as e:
        print(f"[WebSocket] Event replay error: {e}")
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client ping or control messages if sent
    except WebSocketDisconnect:
        manager.disconnect_mission(websocket, mission_id)

# WebSocket Endpoint: Live Browser Lab Screencast Stream
@app.websocket("/ws/stream/{mission_id}")
async def websocket_browser_stream(websocket: WebSocket, mission_id: str):
    await manager.connect_stream(websocket, mission_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_stream(websocket, mission_id)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
