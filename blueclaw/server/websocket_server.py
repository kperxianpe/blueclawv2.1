#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket Server - Integrates with Blueclaw Engine

Exposes Week 15-17 core functionality via WebSocket:
- Intent Analysis
- Thinking Chain (clarification flow)
- Blueprint Generation
- Step Execution
- Intervention & REPLAN
"""

import asyncio
import json
import uuid
from typing import Dict, Set
import websockets
from websockets.server import WebSocketServerProtocol


class BlueclawWebSocketServer:
    """
    Blueclaw WebSocket Server
    
    Bridges WebSocket clients with Blueclaw EngineFacade.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        
        # Connection management
        self.connections: Dict[WebSocketServerProtocol, dict] = {}
        self.task_connections: Dict[str, Set[WebSocketServerProtocol]] = {}
        
        # Engine instances per session
        self.engines: Dict[str, 'BlueclawEngineFacade'] = {}
        
    async def start(self):
        """Start WebSocket server"""
        print(f"Starting Blueclaw WebSocket Server at ws://{self.host}:{self.port}")
        print(f"Core Engine: Week 15-17 Integrated")
        
        async with websockets.serve(self._handle_connection, self.host, self.port):
            await asyncio.Future()  # Run forever
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())[:8]
        self.connections[websocket] = {
            "id": connection_id,
            "session_id": None,
            "connected_at": asyncio.get_event_loop().time()
        }
        print(f"[WS] New connection: {connection_id}")
        
        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[WS] Connection closed: {connection_id}")
        finally:
            await self._cleanup_connection(websocket)
    
    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming message"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            payload = data.get("payload", {})
            
            print(f"[WS] Received: {msg_type}")
            
            # Route to appropriate handler
            handler = getattr(self, f"_handle_{msg_type.replace('.', '_')}", None)
            
            if handler:
                response = await handler(websocket, payload)
            else:
                response = self._error_response(f"Unknown message type: {msg_type}")
            
            await self._send(websocket, response)
            
        except json.JSONDecodeError:
            await self._send(websocket, self._error_response("Invalid JSON"))
        except Exception as e:
            print(f"[WS] Error handling message: {e}")
            await self._send(websocket, self._error_response(str(e)))
    
    # ========== Message Handlers ==========
    
    async def _handle_task_start(self, websocket, payload: dict) -> dict:
        """Handle task.start - Creates new session with EngineFacade"""
        from blueclaw.api import BlueclawEngineFacade
        
        user_input = payload.get("user_input", "")
        session_id = payload.get("session_id") or f"session_{uuid.uuid4().hex[:8]}"
        
        # Create engine instance for this session
        engine = BlueclawEngineFacade(session_id, persistence_path="./sessions")
        engine.set_callbacks(
            on_step_started=lambda step: self._broadcast_step_started(session_id, step),
            on_step_completed=lambda step, result: self._broadcast_step_completed(session_id, step, result),
            on_step_failed=lambda step, result: self._broadcast_step_failed(session_id, step, result),
            on_intervention_needed=lambda data: self._broadcast_intervention(session_id, data)
        )
        
        self.engines[session_id] = engine
        self.connections[websocket]["session_id"] = session_id
        
        # Associate connection with session
        if session_id not in self.task_connections:
            self.task_connections[session_id] = set()
        self.task_connections[session_id].add(websocket)
        
        # Process input through thinking engine
        result = await engine.process(user_input)
        
        return {
            "type": "task.created",
            "payload": {
                "session_id": session_id,
                "phase": result.get("type"),
                "thinking_node": result if result.get("type") == "thinking_node" else None,
                "blueprint": result.get("steps") if result.get("type") in ["blueprint_ready", "execution_preview"] else None
            },
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }
    
    async def _handle_thinking_select_option(self, websocket, payload: dict) -> dict:
        """Handle thinking.select_option"""
        session_id = payload.get("session_id")
        node_id = payload.get("node_id")
        option_id = payload.get("option_id")
        
        engine = self.engines.get(session_id)
        if not engine:
            return self._error_response("Session not found")
        
        result = await engine.select_option(node_id, option_id)
        
        return {
            "type": "thinking.node_selected",
            "payload": {
                "session_id": session_id,
                "phase": result.get("type"),
                "next_node": result if result.get("type") == "thinking_node" else None,
                "blueprint": result.get("steps") if result.get("type") == "blueprint_ready" else None
            },
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }
    
    async def _handle_execution_start(self, websocket, payload: dict) -> dict:
        """Handle execution.start"""
        session_id = payload.get("session_id")
        
        engine = self.engines.get(session_id)
        if not engine:
            return self._error_response("Session not found")
        
        # Start execution
        result = await engine.execute_blueprint()
        
        steps_dict = [self._step_to_dict(s) for s in engine.execution_steps]
        return {
            "type": "execution.blueprint_loaded",
            "payload": {
                "session_id": session_id,
                "status": result.get("status"),
                "blueprint": {
                    "id": session_id,
                    "steps": steps_dict
                },
                "steps": steps_dict,
                "completed_steps": len(engine.completed_steps),
                "failed_steps": len(engine.failed_steps)
            },
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }
    
    async def _handle_execution_intervene(self, websocket, payload: dict) -> dict:
        """Handle execution.intervene - REPLAN, skip, stop"""
        session_id = payload.get("session_id")
        step_id = payload.get("step_id")
        action_type = payload.get("action_type")  # replan, skip, stop, retry
        custom_input = payload.get("custom_input")
        
        engine = self.engines.get(session_id)
        if not engine:
            return self._error_response("Session not found")
        
        result = await engine.intervene(step_id, action_type, custom_input)
        
        return {
            "type": "execution.intervention_result",
            "payload": {
                "session_id": session_id,
                "action": action_type,
                "result_type": result.get("type"),
                "steps": [self._step_to_dict(s) for s in engine.execution_steps] if result.get("type") == "blueprint_replaned" else None,
                "status": result.get("status")
            },
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }
    
    async def _handle_task_status(self, websocket, payload: dict) -> dict:
        """Handle task.status query"""
        session_id = payload.get("session_id")
        
        engine = self.engines.get(session_id)
        if not engine:
            return self._error_response("Session not found")
        
        status = engine.get_status()
        chain = engine.get_thinking_chain()
        
        return {
            "type": "task.status",
            "payload": {
                "session_id": session_id,
                "status": status,
                "thinking_chain": chain,
                "progress": status.get("progress", 0)
            },
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }
    
    async def _handle_task_cancel(self, websocket, payload: dict) -> dict:
        """Handle task.cancel"""
        session_id = payload.get("session_id")
        
        if session_id in self.engines:
            del self.engines[session_id]
        
        return {
            "type": "task.cancelled",
            "payload": {"session_id": session_id},
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }
    
    # ========== Broadcast Handlers ==========
    
    def _broadcast_step_started(self, session_id: str, step):
        """Broadcast step started event"""
        data = {
            "step_id": step.step_id,
            "id": step.step_id,
            "name": step.name,
            "status": step.status.value if hasattr(step.status, 'value') else step.status,
            "started_at": step.started_at
        }
        asyncio.create_task(self._broadcast(session_id, {
            "type": "execution.step_started",
            "payload": data,
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }))
    
    def _broadcast_step_completed(self, session_id: str, step, result=None):
        """Broadcast step completed event"""
        data = {
            "step_id": step.step_id,
            "id": step.step_id,
            "name": step.name,
            "status": step.status.value if hasattr(step.status, 'value') else step.status,
            "completed_at": step.completed_at,
            "output": step.output
        }
        asyncio.create_task(self._broadcast(session_id, {
            "type": "execution.step_completed",
            "payload": data,
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }))
    
    def _broadcast_step_failed(self, session_id: str, step, result=None):
        """Broadcast step failed event"""
        data = {
            "step_id": step.step_id,
            "id": step.step_id,
            "name": step.name,
            "status": step.status.value if hasattr(step.status, 'value') else step.status,
            "error": step.error
        }
        asyncio.create_task(self._broadcast(session_id, {
            "type": "execution.step_failed",
            "payload": data,
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }))
    
    def _broadcast_intervention(self, session_id: str, data: dict):
        """Broadcast intervention needed event"""
        asyncio.create_task(self._broadcast(session_id, {
            "type": "execution.intervention_needed",
            "payload": data,
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }))
    
    async def _broadcast(self, session_id: str, message: dict):
        """Broadcast message to all connections for a session"""
        if session_id not in self.task_connections:
            return
        
        websockets_set = self.task_connections[session_id].copy()
        for ws in websockets_set:
            try:
                await ws.send(json.dumps(message))
            except:
                pass
    
    # ========== Utility Methods ==========
    
    async def _send(self, websocket: WebSocketServerProtocol, message: dict):
        """Send message to client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            pass
    
    async def _cleanup_connection(self, websocket: WebSocketServerProtocol):
        """Clean up disconnected client"""
        if websocket in self.connections:
            conn_info = self.connections[websocket]
            session_id = conn_info.get("session_id")
            
            if session_id and session_id in self.task_connections:
                self.task_connections[session_id].discard(websocket)
                if not self.task_connections[session_id]:
                    del self.task_connections[session_id]
            
            del self.connections[websocket]
    
    def _error_response(self, message: str) -> dict:
        """Create error response"""
        return {
            "type": "error",
            "payload": {"message": message},
            "timestamp": self._timestamp(),
            "message_id": str(uuid.uuid4())
        }
    
    def _step_to_dict(self, step) -> dict:
        """Convert ExecutionStep to dict"""
        return {
            "id": step.step_id,
            "step_id": step.step_id,
            "name": step.name,
            "description": step.description,
            "status": step.status.value,
            "tool": step.tool,
            "dependencies": step.dependencies
        }
    
    def _timestamp(self) -> int:
        """Get current timestamp in ms"""
        return int(asyncio.get_event_loop().time() * 1000)
