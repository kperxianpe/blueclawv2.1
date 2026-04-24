# -*- coding: utf-8 -*-
"""
message_protocol.py - Blueclaw 消息协议定义（版本化）

协议版本: 1.0.0
设计原则:
- 消息格式向前兼容，支持 V1/V2/V3
- 所有消息包含版本标识
- payload 使用灵活的字典结构，便于扩展
"""

from __future__ import annotations

import uuid
import time
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict


# 协议版本
PROTOCOL_VERSION = "1.0.0"


class MessageType(str, Enum):
    """消息类型枚举 - 客户端到服务端"""
    # Client -> Server
    TASK_START = "task.start"
    THINKING_SELECT_OPTION = "thinking.select_option"
    THINKING_CUSTOM_INPUT = "thinking.custom_input"
    THINKING_CONFIRM_EXECUTION = "thinking.confirm_execution"
    EXECUTION_INTERVENE = "execution.intervene"
    EXECUTION_PAUSE = "execution.pause"
    EXECUTION_RESUME = "execution.resume"
    
    # Server -> Client
    THINKING_NODE_CREATED = "thinking.node_created"
    THINKING_NODE_SELECTED = "thinking.node_selected"
    EXECUTION_BLUEPRINT_LOADED = "execution.blueprint_loaded"
    EXECUTION_STEP_STARTED = "execution.step_started"
    EXECUTION_STEP_COMPLETED = "execution.step_completed"
    EXECUTION_STEP_FAILED = "execution.step_failed"
    EXECUTION_INTERVENTION_NEEDED = "execution.intervention_needed"
    EXECUTION_REPLANNED = "execution.replanned"
    EXECUTION_COMPLETED = "execution.completed"
    
    # System
    ERROR = "system.error"
    PING = "system.ping"
    PONG = "system.pong"
    CONNECTED = "system.connected"
    DISCONNECTED = "system.disconnected"


class NodeStatus(str, Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SELECTED = "selected"
    SKIPPED = "skipped"


class Phase(str, Enum):
    """应用阶段"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    INTERVENING = "intervening"
    COMPLETED = "completed"


# ==================== 数据模型 ====================

@dataclass
class ThinkingOptionData:
    """思考选项数据 - 纯数据结构"""
    id: str
    label: str
    description: str
    confidence: float
    is_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThinkingOptionData":
        return cls(**data)


@dataclass
class ThinkingNodeData:
    """思考节点数据 - 纯数据结构，不含渲染信息"""
    id: str
    type: str = "thinking"  # 'thinking' | 'execution'
    question: str = ""
    options: List[ThinkingOptionData] = field(default_factory=list)
    selected_option: Optional[str] = None
    custom_input: Optional[str] = None
    status: str = NodeStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "question": self.question,
            "options": [opt.to_dict() for opt in self.options],
            "selected_option": self.selected_option,
            "custom_input": self.custom_input,
            "status": self.status,
            "metadata": {
                **self.metadata,
                "created_at": time.time(),
                "version": PROTOCOL_VERSION
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThinkingNodeData":
        options = [ThinkingOptionData.from_dict(opt) for opt in data.get("options", [])]
        return cls(
            id=data["id"],
            type=data.get("type", "thinking"),
            question=data.get("question", ""),
            options=options,
            selected_option=data.get("selected_option"),
            custom_input=data.get("custom_input"),
            status=data.get("status", NodeStatus.PENDING),
            metadata=data.get("metadata", {})
        )


@dataclass
class ExecutionStepData:
    """执行步骤数据 - 纯数据结构"""
    id: str
    type: str = "execution"
    name: str = ""
    description: str = ""
    status: str = NodeStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": {
                **self.metadata,
                "version": PROTOCOL_VERSION
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionStepData":
        return cls(
            id=data["id"],
            type=data.get("type", "execution"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=data.get("status", NodeStatus.PENDING),
            dependencies=data.get("dependencies", []),
            result=data.get("result"),
            error=data.get("error"),
            duration_ms=data.get("duration_ms"),
            metadata=data.get("metadata", {})
        )


@dataclass
class InterventionActionData:
    """干预动作数据"""
    type: str  # 'replan', 'skip', 'stop', 'retry'
    label: str
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BlueclawMessage:
    """
    Blueclaw 标准消息格式
    
    所有通信消息必须遵循此格式，确保前后端兼容
    """
    type: MessageType
    payload: Dict[str, Any] = field(default_factory=dict)
    version: str = PROTOCOL_VERSION
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            "version": self.version,
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlueclawMessage":
        """从字典创建消息"""
        msg_type = data.get("type", "")
        # 支持字符串或枚举
        if isinstance(msg_type, str):
            try:
                msg_type = MessageType(msg_type)
            except ValueError:
                pass
        
        return cls(
            type=msg_type,
            payload=data.get("payload", {}),
            version=data.get("version", PROTOCOL_VERSION),
            timestamp=data.get("timestamp", int(time.time() * 1000)),
            message_id=data.get("message_id", str(uuid.uuid4())[:8])
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "BlueclawMessage":
        """从JSON字符串创建消息"""
        import json
        return cls.from_dict(json.loads(json_str))


# ==================== 消息工厂方法 ====================

class MessageFactory:
    """消息工厂 - 便捷创建各类消息"""
    
    @staticmethod
    def create_task_start(user_input: str, context: Optional[Dict] = None) -> BlueclawMessage:
        """创建任务开始消息"""
        return BlueclawMessage(
            type=MessageType.TASK_START,
            payload={
                "user_input": user_input,
                "context": context or {}
            }
        )
    
    @staticmethod
    def create_thinking_node_created(node: ThinkingNodeData) -> BlueclawMessage:
        """创建思考节点消息"""
        return BlueclawMessage(
            type=MessageType.THINKING_NODE_CREATED,
            payload=node.to_dict()
        )
    
    @staticmethod
    def create_thinking_select_option(node_id: str, option_id: str) -> BlueclawMessage:
        """创建选择选项消息"""
        return BlueclawMessage(
            type=MessageType.THINKING_SELECT_OPTION,
            payload={
                "node_id": node_id,
                "option_id": option_id
            }
        )
    
    @staticmethod
    def create_execution_blueprint_loaded(steps: List[ExecutionStepData]) -> BlueclawMessage:
        """创建执行蓝图加载消息"""
        return BlueclawMessage(
            type=MessageType.EXECUTION_BLUEPRINT_LOADED,
            payload={
                "steps": [step.to_dict() for step in steps],
                "total_steps": len(steps)
            }
        )
    
    @staticmethod
    def create_execution_step_started(step_id: str, step_name: str, index: int) -> BlueclawMessage:
        """创建步骤开始消息"""
        return BlueclawMessage(
            type=MessageType.EXECUTION_STEP_STARTED,
            payload={
                "step_id": step_id,
                "step_name": step_name,
                "index": index
            }
        )
    
    @staticmethod
    def create_execution_step_completed(step_id: str, result: Any, duration_ms: float) -> BlueclawMessage:
        """创建步骤完成消息"""
        return BlueclawMessage(
            type=MessageType.EXECUTION_STEP_COMPLETED,
            payload={
                "step_id": step_id,
                "result": result,
                "duration_ms": duration_ms
            }
        )
    
    @staticmethod
    def create_execution_step_failed(step_id: str, error: str) -> BlueclawMessage:
        """创建步骤失败消息"""
        return BlueclawMessage(
            type=MessageType.EXECUTION_STEP_FAILED,
            payload={
                "step_id": step_id,
                "error": error
            }
        )
    
    @staticmethod
    def create_execution_intervention_needed(
        step_id: str, 
        step_name: str, 
        reason: str,
        actions: List[InterventionActionData]
    ) -> BlueclawMessage:
        """创建需要干预消息"""
        return BlueclawMessage(
            type=MessageType.EXECUTION_INTERVENTION_NEEDED,
            payload={
                "step_id": step_id,
                "step_name": step_name,
                "reason": reason,
                "actions": [action.to_dict() for action in actions]
            }
        )
    
    @staticmethod
    def create_execution_intervene(step_id: str, action_type: str, custom_input: Optional[str] = None) -> BlueclawMessage:
        """创建干预动作消息"""
        return BlueclawMessage(
            type=MessageType.EXECUTION_INTERVENE,
            payload={
                "step_id": step_id,
                "action_type": action_type,
                "custom_input": custom_input
            }
        )
    
    @staticmethod
    def create_execution_completed(success: bool, summary: str, **kwargs) -> BlueclawMessage:
        """创建执行完成消息"""
        return BlueclawMessage(
            type=MessageType.EXECUTION_COMPLETED,
            payload={
                "success": success,
                "summary": summary,
                **kwargs
            }
        )
    
    @staticmethod
    def create_error(error_code: str, error_message: str, details: Optional[Dict] = None) -> BlueclawMessage:
        """创建错误消息"""
        return BlueclawMessage(
            type=MessageType.ERROR,
            payload={
                "error_code": error_code,
                "error_message": error_message,
                "details": details or {}
            }
        )
    
    @staticmethod
    def create_connected(session_id: str) -> BlueclawMessage:
        """创建连接成功消息"""
        return BlueclawMessage(
            type=MessageType.CONNECTED,
            payload={
                "session_id": session_id,
                "protocol_version": PROTOCOL_VERSION,
                "server_info": {
                    "name": "Blueclaw Server",
                    "version": "1.0.0"
                }
            }
        )
    
    @staticmethod
    def create_ping() -> BlueclawMessage:
        """创建ping消息"""
        return BlueclawMessage(type=MessageType.PING)
    
    @staticmethod
    def create_pong() -> BlueclawMessage:
        """创建pong消息"""
        return BlueclawMessage(type=MessageType.PONG)


# ==================== 版本兼容性检查 ====================

def check_version_compatibility(client_version: str) -> Dict[str, Any]:
    """
    检查客户端版本兼容性
    
    Returns:
        {
            "compatible": bool,
            "message": str,
            "server_version": str
        }
    """
    # V1.0.0 协议与相同主版本号的客户端兼容
    client_parts = client_version.split(".")
    server_parts = PROTOCOL_VERSION.split(".")
    
    # 主版本号必须相同
    if client_parts[0] != server_parts[0]:
        return {
            "compatible": False,
            "message": f"版本不兼容: 客户端 v{client_version}, 服务端 v{PROTOCOL_VERSION}",
            "server_version": PROTOCOL_VERSION
        }
    
    # 次版本号客户端可以低于服务端
    if len(client_parts) >= 2 and len(server_parts) >= 2:
        if int(client_parts[1]) > int(server_parts[1]):
            return {
                "compatible": False,
                "message": f"客户端版本 v{client_version} 高于服务端 v{PROTOCOL_VERSION}",
                "server_version": PROTOCOL_VERSION
            }
    
    return {
        "compatible": True,
        "message": f"版本兼容: v{client_version}",
        "server_version": PROTOCOL_VERSION
    }


# ==================== 导出便捷函数 ====================

def create_message(
    msg_type: Union[MessageType, str],
    payload: Dict[str, Any] = None,
    **kwargs
) -> BlueclawMessage:
    """便捷函数：创建消息"""
    if isinstance(msg_type, str):
        msg_type = MessageType(msg_type)
    
    return BlueclawMessage(
        type=msg_type,
        payload=payload or {},
        **kwargs
    )
