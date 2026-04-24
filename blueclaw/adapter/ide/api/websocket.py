# -*- coding: utf-8 -*-
"""
IDE WebSocket - 实时通信

前端连接 ws://host/ws/ide 后，后端主动推送：
- 文件变更通知
- 终端输出
- 测试进度
- KimiCode 流式输出
"""
import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect


class IDEWebSocketManager:
    """IDE WebSocket 连接管理器"""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        payload = json.dumps(message, ensure_ascii=False, default=str)
        async with self._lock:
            dead = set()
            for ws in self._connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)
            self._connections -= dead

    async def send_to(self, websocket: WebSocket, message: dict):
        """发送给单个连接"""
        payload = json.dumps(message, ensure_ascii=False, default=str)
        try:
            await websocket.send_text(payload)
        except Exception:
            pass


# Global manager instance
manager = IDEWebSocketManager()


async def handle_ide_websocket(websocket: WebSocket):
    """WebSocket 处理入口"""
    await manager.connect(websocket)
    try:
        while True:
            # Receive frontend messages (ping, subscription, etc.)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                if msg_type == "ping":
                    await manager.send_to(websocket, {"type": "pong"})
                elif msg_type == "subscribe":
                    channel = msg.get("channel")
                    await manager.send_to(websocket, {"type": "subscribed", "channel": channel})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


# Convenience broadcast helpers

async def notify_fs_change(path: str, event: str = "modified"):
    await manager.broadcast({"type": "fs.change", "path": path, "event": event})


async def notify_run_output(run_id: str, data: str, output_type: str = "stdout"):
    await manager.broadcast({"type": "run.output", "run_id": run_id, "output_type": output_type, "data": data})


async def notify_test_progress(test_run_id: str, completed: int, total: int):
    await manager.broadcast({"type": "test.progress", "test_run_id": test_run_id, "completed": completed, "total": total})


async def notify_kimicode_chunk(session_id: str, content: str):
    await manager.broadcast({"type": "kimicode.chunk", "session_id": session_id, "content": content})


async def notify_error(message: str, details: str = ""):
    await manager.broadcast({"type": "error", "message": message, "details": details})
