# -*- coding: utf-8 -*-
"""
websocket_server.py - Blueclaw WebSocket 服务器

提供实时双向通信，使用标准消息协议。
支持多客户端连接，每个连接有独立的引擎实例。
"""

from __future__ import annotations

import asyncio
import json
import websockets
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import asdict

from .message_protocol import (
    BlueclawMessage,
    MessageType,
    MessageFactory,
    ThinkingNodeData,
    ExecutionStepData,
    InterventionActionData,
    check_version_compatibility,
    PROTOCOL_VERSION
)
from .engine_facade import (
    BlueclawEngineFacade,
    EngineState,
    create_engine_facade
)


class ConnectionHandler:
    """
    单个WebSocket连接的处理程序
    
    每个连接有独立的引擎实例，确保会话隔离
    """
    
    def __init__(self, websocket: websockets.WebSocketServerProtocol, server: "BlueclawWebSocketServer"):
        self.websocket = websocket
        self.server = server
        self.session_id: str = ""
        self.engine: Optional[BlueclawEngineFacade] = None
        self.connected: bool = False
        self._ping_task: Optional[asyncio.Task] = None
    
    async def handle(self):
        """处理连接"""
        self.connected = True
        self.session_id = str(id(self.websocket))[:8]
        
        # 创建引擎实例
        self.engine = create_engine_facade(self.session_id)
        self.engine.set_callbacks(
            on_thinking_node_created=self._on_thinking_node_created,
            on_option_selected=self._on_option_selected,
            on_blueprint_loaded=self._on_blueprint_loaded,
            on_step_status_changed=self._on_step_status_changed,
            on_execution_completed=self._on_execution_completed,
            on_intervention_needed=self._on_intervention_needed,
            state_changed=self._on_state_changed,
            message=self._on_engine_message
        )
        
        # 注册到服务器
        self.server.register_connection(self.session_id, self)
        
        # 发送连接成功消息
        await self.send_message(MessageFactory.create_connected(self.session_id))
        
        print(f"[WS] Client connected: {self.session_id}")
        
        # 启动ping任务
        self._ping_task = asyncio.create_task(self._ping_loop())
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[WS] Client disconnected: {self.session_id}")
        finally:
            self.connected = False
            if self._ping_task:
                self._ping_task.cancel()
            self.server.unregister_connection(self.session_id)
    
    async def _handle_message(self, raw_message: str):
        """处理客户端消息"""
        try:
            # 解析消息
            data = json.loads(raw_message)
            message = BlueclawMessage.from_dict(data)
            
            print(f"[WS] Received: {message.type}")
            
            # 检查版本兼容性
            if message.version != PROTOCOL_VERSION:
                compat = check_version_compatibility(message.version)
                if not compat["compatible"]:
                    await self.send_message(MessageFactory.create_error(
                        "VERSION_MISMATCH",
                        compat["message"]
                    ))
                    return
            
            # 路由到对应的处理函数
            handler = self._get_handler(message.type)
            if handler:
                await handler(message)
            else:
                await self.send_message(MessageFactory.create_error(
                    "UNKNOWN_MESSAGE_TYPE",
                    f"Unknown message type: {message.type}"
                ))
                
        except json.JSONDecodeError as e:
            await self.send_message(MessageFactory.create_error(
                "INVALID_JSON",
                f"Invalid JSON: {str(e)}"
            ))
        except Exception as e:
            print(f"[WS] Error handling message: {e}")
            await self.send_message(MessageFactory.create_error(
                "INTERNAL_ERROR",
                str(e)
            ))
    
    def _get_handler(self, msg_type: MessageType) -> Optional[Callable]:
        """获取消息处理器"""
        handlers = {
            MessageType.TASK_START: self._handle_task_start,
            MessageType.THINKING_SELECT_OPTION: self._handle_select_option,
            MessageType.THINKING_CUSTOM_INPUT: self._handle_custom_input,
            MessageType.THINKING_CONFIRM_EXECUTION: self._handle_confirm_execution,
            MessageType.EXECUTION_INTERVENE: self._handle_intervene,
            MessageType.EXECUTION_PAUSE: self._handle_pause,
            MessageType.EXECUTION_RESUME: self._handle_resume,
            MessageType.PING: self._handle_ping,
        }
        
        # 支持字符串类型
        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)
        
        return handlers.get(msg_type)
    
    # ============ 消息处理器 ============
    
    async def _handle_task_start(self, message: BlueclawMessage):
        """处理任务开始"""
        user_input = message.payload.get("user_input", "")
        context = message.payload.get("context", {})
        
        if not user_input:
            await self.send_message(MessageFactory.create_error(
                "MISSING_INPUT",
                "user_input is required"
            ))
            return
        
        # 异步处理任务
        result = await self.engine.process(user_input, context)
        
        # 如果是直接回答，发送完成消息
        if result.direct_answer:
            await self.send_message(MessageFactory.create_execution_completed(
                success=True,
                summary=result.direct_answer,
                result_type="direct_answer"
            ))
    
    async def _handle_select_option(self, message: BlueclawMessage):
        """处理选项选择"""
        node_id = message.payload.get("node_id", "")
        option_id = message.payload.get("option_id", "")
        
        if not node_id or not option_id:
            await self.send_message(MessageFactory.create_error(
                "MISSING_PARAMS",
                "node_id and option_id are required"
            ))
            return
        
        result = await self.engine.select_option(node_id, option_id)
        
        # 发送选择确认
        await self.send_message(BlueclawMessage(
            type=MessageType.THINKING_NODE_SELECTED,
            payload={
                "node_id": node_id,
                "option_id": option_id,
                "result_type": result.result_type
            }
        ))
    
    async def _handle_custom_input(self, message: BlueclawMessage):
        """处理自定义输入"""
        node_id = message.payload.get("node_id", "")
        custom_input = message.payload.get("custom_input", "")
        
        if not node_id or not custom_input:
            await self.send_message(MessageFactory.create_error(
                "MISSING_PARAMS",
                "node_id and custom_input are required"
            ))
            return
        
        result = await self.engine.provide_clarification(node_id, custom_input)
        
        # 发送处理结果
        if result.direct_answer:
            await self.send_message(MessageFactory.create_execution_completed(
                success=True,
                summary=result.direct_answer
            ))
    
    async def _handle_confirm_execution(self, message: BlueclawMessage):
        """处理执行确认"""
        confirmed = message.payload.get("confirmed", True)
        
        if confirmed:
            # 继续执行已在引擎中处理
            pass
        else:
            # 用户取消，发送完成消息
            await self.send_message(MessageFactory.create_execution_completed(
                success=False,
                summary="用户取消执行"
            ))
    
    async def _handle_intervene(self, message: BlueclawMessage):
        """处理干预请求"""
        step_id = message.payload.get("step_id", "")
        action_type = message.payload.get("action_type", "")
        custom_input = message.payload.get("custom_input")
        
        if not step_id or not action_type:
            await self.send_message(MessageFactory.create_error(
                "MISSING_PARAMS",
                "step_id and action_type are required"
            ))
            return
        
        result = await self.engine.intervene(step_id, action_type, custom_input)
        
        # 发送重新规划结果
        if result.success and result.new_steps:
            await self.send_message(BlueclawMessage(
                type=MessageType.EXECUTION_REPLANNED,
                payload={
                    "step_id": step_id,
                    "new_steps": result.new_steps,
                    "message": result.message
                }
            ))
    
    async def _handle_pause(self, message: BlueclawMessage):
        """处理暂停请求"""
        self.engine.pause_execution()
        await self.send_message(BlueclawMessage(
            type=MessageType.EXECUTION_PAUSE,
            payload={"status": "paused"}
        ))
    
    async def _handle_resume(self, message: BlueclawMessage):
        """处理恢复请求"""
        self.engine.resume_execution()
        await self.send_message(BlueclawMessage(
            type=MessageType.EXECUTION_RESUME,
            payload={"status": "resumed"}
        ))
    
    async def _handle_ping(self, message: BlueclawMessage):
        """处理ping"""
        await self.send_message(MessageFactory.create_pong())
    
    # ============ 引擎回调 ============
    
    def _on_thinking_node_created(self, node: ThinkingNodeData):
        """思考节点创建回调"""
        asyncio.create_task(self.send_message(
            MessageFactory.create_thinking_node_created(node)
        ))
    
    def _on_option_selected(self, node_id: str, option_id: str):
        """选项选择回调"""
        pass  # 已在前端处理
    
    def _on_blueprint_loaded(self, steps: list):
        """蓝图加载回调"""
        execution_steps = [
            step if isinstance(step, ExecutionStepData) else ExecutionStepData(**step)
            for step in steps
        ]
        asyncio.create_task(self.send_message(
            MessageFactory.create_execution_blueprint_loaded(execution_steps)
        ))
    
    def _on_step_status_changed(self, step_id: str, status: str, index: int):
        """步骤状态变化回调"""
        step = self.engine.get_execution_steps()[index] if index >= 0 else None
        
        if status == "running":
            asyncio.create_task(self.send_message(
                MessageFactory.create_execution_step_started(
                    step_id=step_id,
                    step_name=step.name if step else "",
                    index=index
                )
            ))
        elif status == "completed":
            asyncio.create_task(self.send_message(
                MessageFactory.create_execution_step_completed(
                    step_id=step_id,
                    result=step.result if step else None,
                    duration_ms=step.duration_ms if step else 0
                )
            ))
        elif status == "failed":
            asyncio.create_task(self.send_message(
                MessageFactory.create_execution_step_failed(
                    step_id=step_id,
                    error=step.error if step else "Unknown error"
                )
            ))
    
    def _on_execution_completed(self, success: bool, summary: str):
        """执行完成回调"""
        asyncio.create_task(self.send_message(
            MessageFactory.create_execution_completed(
                success=success,
                summary=summary
            )
        ))
    
    def _on_intervention_needed(self, step_id: str, reason: str, actions: list):
        """需要干预回调"""
        action_data = [
            action if isinstance(action, InterventionActionData) else InterventionActionData(**action)
            for action in actions
        ]
        
        step = self.engine.get_current_step()
        asyncio.create_task(self.send_message(
            MessageFactory.create_execution_intervention_needed(
                step_id=step_id,
                step_name=step.name if step else "",
                reason=reason,
                actions=action_data
            )
        ))
    
    def _on_state_changed(self, state: EngineState):
        """状态变化回调"""
        # 状态变化通过其他消息同步，这里不需要额外发送
        pass
    
    def _on_engine_message(self, message: str):
        """引擎日志消息回调"""
        # 可以发送日志消息到客户端
        pass
    
    # ============ 辅助方法 ============
    
    async def send_message(self, message: BlueclawMessage):
        """发送消息到客户端"""
        if self.connected:
            try:
                await self.websocket.send(message.to_json())
            except websockets.exceptions.ConnectionClosed:
                print(f"[WS] Failed to send, connection closed: {self.session_id}")
    
    async def _ping_loop(self):
        """定期发送ping"""
        while self.connected:
            try:
                await asyncio.sleep(30)  # 每30秒ping一次
                if self.connected:
                    await self.send_message(MessageFactory.create_ping())
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WS] Ping error: {e}")


class BlueclawWebSocketServer:
    """
    Blueclaw WebSocket 服务器
    
    管理所有客户端连接，路由消息到对应的连接处理器
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.connections: Dict[str, ConnectionHandler] = {}
        self.server: Optional[websockets.WebSocketServer] = None
    
    def register_connection(self, session_id: str, handler: ConnectionHandler):
        """注册连接"""
        self.connections[session_id] = handler
    
    def unregister_connection(self, session_id: str):
        """注销连接"""
        if session_id in self.connections:
            del self.connections[session_id]
    
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str = None):
        """处理新客户端连接"""
        handler = ConnectionHandler(websocket, self)
        await handler.handle()
    
    async def start(self):
        """启动服务器"""
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=None  # 我们自己处理ping
        )
        
        print(f"[WS] Server started at ws://{self.host}:{self.port}")
        
        # 保持运行
        await self.server.wait_closed()
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.close()


def create_server(host: str = "localhost", port: int = 8765) -> BlueclawWebSocketServer:
    """创建WebSocket服务器实例"""
    return BlueclawWebSocketServer(host, port)


async def main():
    """主函数 - 用于测试"""
    server = create_server()
    
    # 设置 graceful shutdown
    loop = asyncio.get_event_loop()
    
    def shutdown():
        print("\n[WS] Shutting down...")
        server.stop()
    
    # 处理 Ctrl+C
    import signal
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)
    
    try:
        await server.start()
    except asyncio.CancelledError:
        pass
    finally:
        print("[WS] Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
