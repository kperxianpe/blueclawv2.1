#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw WebSocket 服务主入口
"""
import asyncio
import json
import uuid
from typing import Dict, Set, Optional
import websockets
from websockets.server import WebSocketServerProtocol


class BlueclawWebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        # 存储所有连接: {websocket: connection_info}
        self.connections: Dict[WebSocketServerProtocol, dict] = {}
        # 按任务分组: {task_id: Set[websocket]}
        self.task_connections: Dict[str, Set[WebSocketServerProtocol]] = {}
        
    async def start(self):
        """启动 WebSocket 服务"""
        print(f"Starting WebSocket server at ws://{self.host}:{self.port}")
        
        # 设置消息路由器的 WebSocket 服务器引用
        from backend.websocket.message_router import router
        router.set_websocket_server(self)
        print("[Server] Message router initialized")
        
        async with websockets.serve(
            self._handle_connection, 
            self.host, 
            self.port,
            ping_interval=20,
            ping_timeout=10
        ):
            print(f"[Server] Ready! Listening on ws://{self.host}:{self.port}")
            await asyncio.Future()  # 永远运行
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol):
        """处理新连接"""
        connection_id = str(uuid.uuid4())
        self.connections[websocket] = {
            "id": connection_id,
            "connected_at": asyncio.get_event_loop().time(),
            "task_id": None
        }
        print(f"New connection: {connection_id}")
        
        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection closed: {connection_id}")
        finally:
            await self._cleanup_connection(websocket)
    
    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            payload = data.get("payload", {})
            print(f"[Message] Received: {msg_type}")
            
            # 自动关联：如果消息包含 task_id，将当前连接关联到该任务
            task_id = payload.get("task_id") if isinstance(payload, dict) else None
            if task_id and websocket in self.connections:
                current_task = self.connections[websocket].get("task_id")
                if current_task != task_id:
                    self.associate_connection_with_task(websocket, task_id)
                    print(f"[Message] Auto-associated connection with task: {task_id}")
            
            # 导入路由器处理消息
            from backend.websocket.message_router import router
            response = await router.route(websocket, data, self)
            
            # 发送响应
            await self.send_to_connection(websocket, response)
            print(f"[Message] Sent response for: {msg_type}")
            
        except json.JSONDecodeError as e:
            print(f"[Error] Invalid JSON: {e}")
            await self.send_to_connection(websocket, {
                "type": "error",
                "payload": {"message": "Invalid JSON"},
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
                "message_id": str(uuid.uuid4())
            })
        except Exception as e:
            print(f"[Error] Handler failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self.send_to_connection(websocket, {
                "type": "error",
                "payload": {"message": str(e)},
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
                "message_id": str(uuid.uuid4())
            })
    
    async def send_to_connection(self, websocket: WebSocketServerProtocol, message: dict):
        """向单个连接发送消息（带超时保护，避免僵尸连接阻塞广播）"""
        try:
            import asyncio
            await asyncio.wait_for(websocket.send(json.dumps(message)), timeout=2.0)
        except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError, OSError):
            pass
    
    async def broadcast_to_task(self, task_id: str, message: dict):
        """向同一任务的所有连接广播消息（并发发送，避免单连接阻塞）"""
        if task_id not in self.task_connections:
            return
        
        import asyncio
        websockets_set = self.task_connections[task_id].copy()
        if not websockets_set:
            return
        
        # 并发发送，避免单个僵尸连接阻塞整个广播
        tasks = [asyncio.create_task(self.send_to_connection(ws, message)) for ws in websockets_set]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 发送完成后清理已断开的连接
        for ws in websockets_set:
            if getattr(ws, 'state', None) != 1:
                self.task_connections[task_id].discard(ws)
        if not self.task_connections[task_id]:
            del self.task_connections[task_id]
    
    async def _cleanup_connection(self, websocket: WebSocketServerProtocol):
        """清理断开连接的客户端"""
        if websocket in self.connections:
            conn_info = self.connections[websocket]
            task_id = conn_info.get("task_id")
            
            # 从任务分组中移除
            if task_id and task_id in self.task_connections:
                self.task_connections[task_id].discard(websocket)
                if not self.task_connections[task_id]:
                    del self.task_connections[task_id]
            
            del self.connections[websocket]
    
    def get_task_id_for_connection(self, websocket: WebSocketServerProtocol) -> Optional[str]:
        """Get the task_id associated with a websocket connection."""
        if websocket in self.connections:
            return self.connections[websocket].get("task_id")
        return None

    def associate_connection_with_task(self, websocket: WebSocketServerProtocol, task_id: str):
        """将连接与任务关联"""
        if websocket in self.connections:
            self.connections[websocket]["task_id"] = task_id
        
        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(websocket)
