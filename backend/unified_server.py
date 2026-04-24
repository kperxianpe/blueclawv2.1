#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Server — FastAPI + WebSocket hybrid entry for v2.5

Combines:
- FastAPI HTTP REST (IDE API at /api/ide/*)
- Main WebSocket endpoint (/ws) for task lifecycle + adapter runtime
- IDE WebSocket endpoint (/ws/ide) for IDE real-time push
"""
import asyncio
import json
import uuid
from typing import Dict, Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Blueclaw v2.5 Unified Server")

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UnifiedServer:
    """Replaces BlueclawWebSocketServer with FastAPI-compatible implementation."""

    def __init__(self):
        self.connections: Dict[WebSocket, dict] = {}
        self.task_connections: Dict[str, Set[WebSocket]] = {}

    async def handle_main_ws(self, websocket: WebSocket):
        """Handle /ws endpoint (task lifecycle + adapter runtime)."""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.connections[websocket] = {
            "id": connection_id,
            "connected_at": asyncio.get_event_loop().time(),
            "task_id": None,
        }
        print(f"[WS] New connection: {connection_id}")

        try:
            while True:
                message = await websocket.receive_text()
                await self._handle_message(websocket, message)
        except WebSocketDisconnect:
            print(f"[WS] Connection closed: {connection_id}")
        except Exception as e:
            print(f"[WS] Error: {e}")
        finally:
            await self._cleanup_connection(websocket)

    async def _handle_message(self, websocket: WebSocket, message: str):
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            payload = data.get("payload", {})
            print(f"[WS] Received: {msg_type}")

            # Auto-associate task
            task_id = payload.get("task_id") if isinstance(payload, dict) else None
            if task_id and websocket in self.connections:
                current_task = self.connections[websocket].get("task_id")
                if current_task != task_id:
                    self.associate_connection_with_task(websocket, task_id)
                    print(f"[WS] Auto-associated with task: {task_id}")

            from backend.websocket.message_router import router
            response = await router.route(websocket, data, self)

            await self.send_to_connection(websocket, response)
            print(f"[WS] Sent response for: {msg_type}")

        except json.JSONDecodeError as e:
            print(f"[WS] Invalid JSON: {e}")
            await self.send_to_connection(websocket, {
                "type": "error",
                "payload": {"message": "Invalid JSON"},
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
                "message_id": str(uuid.uuid4()),
            })
        except Exception as e:
            print(f"[WS] Handler failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self.send_to_connection(websocket, {
                "type": "error",
                "payload": {"message": str(e)},
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
                "message_id": str(uuid.uuid4()),
            })

    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send to a single connection with disconnect handling."""
        try:
            await asyncio.wait_for(websocket.send_text(json.dumps(message)), timeout=2.0)
        except (WebSocketDisconnect, asyncio.TimeoutError, OSError, RuntimeError):
            pass

    async def broadcast_to_task(self, task_id: str, message: dict):
        """Broadcast to all connections associated with a task."""
        if task_id not in self.task_connections:
            return

        websockets_set = self.task_connections[task_id].copy()
        if not websockets_set:
            return

        tasks = [asyncio.create_task(self.send_to_connection(ws, message)) for ws in websockets_set]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Clean up disconnected connections
        closed = [ws for ws in websockets_set if ws not in self.connections]
        for ws in closed:
            self.task_connections[task_id].discard(ws)
        if not self.task_connections[task_id]:
            del self.task_connections[task_id]

    async def _cleanup_connection(self, websocket: WebSocket):
        if websocket in self.connections:
            conn_info = self.connections[websocket]
            task_id = conn_info.get("task_id")

            if task_id and task_id in self.task_connections:
                self.task_connections[task_id].discard(websocket)
                if not self.task_connections[task_id]:
                    del self.task_connections[task_id]

            del self.connections[websocket]

    def get_task_id_for_connection(self, websocket: WebSocket) -> Optional[str]:
        """Get the task_id associated with a websocket connection."""
        if websocket in self.connections:
            return self.connections[websocket].get("task_id")
        return None

    def associate_connection_with_task(self, websocket: WebSocket, task_id: str):
        if websocket in self.connections:
            self.connections[websocket]["task_id"] = task_id

        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(websocket)


# Singleton instance
unified_server = UnifiedServer()


@app.websocket("/ws")
async def main_websocket_endpoint(websocket: WebSocket):
    await unified_server.handle_main_ws(websocket)


# Mount IDE routes (will also add /ws/ide)
from blueclaw.adapter.ide.api.router import register_ide_routes
register_ide_routes(app, workspace_path=".")
