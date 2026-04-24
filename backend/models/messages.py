#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
所有 WebSocket 消息类型定义
"""
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import time


class MessageType(Enum):
    # 客户端 → 服务端
    TASK_START = "task.start"
    THINKING_SELECT_OPTION = "thinking.select_option"
    THINKING_CUSTOM_INPUT = "thinking.custom_input"
    THINKING_CONFIRM_EXECUTION = "thinking.confirm_execution"
    EXECUTION_START = "execution.start"
    EXECUTION_PAUSE = "execution.pause"
    EXECUTION_RESUME = "execution.resume"
    EXECUTION_INTERVENE = "execution.intervene"
    
    # 服务端 → 客户端
    TASK_CREATED = "task.created"
    THINKING_NODE_CREATED = "thinking.node_created"
    THINKING_NODE_SELECTED = "thinking.node_selected"
    THINKING_COMPLETED = "thinking.completed"
    EXECUTION_BLUEPRINT_LOADED = "execution.blueprint_loaded"
    EXECUTION_STEP_STARTED = "execution.step_started"
    EXECUTION_STEP_COMPLETED = "execution.step_completed"
    EXECUTION_STEP_FAILED = "execution.step_failed"
    EXECUTION_INTERVENTION_NEEDED = "execution.intervention_needed"
    EXECUTION_COMPLETED = "execution.completed"
    TASK_STATUS_UPDATED = "task.status_updated"
    TASK_CANCELLED = "task.cancelled"
    
    # 错误
    ERROR = "error"
    ECHO = "echo"  # 调试用


@dataclass
class Message:
    type: str
    payload: Dict[str, Any]
    timestamp: int
    message_id: str
    task_id: Optional[str] = None
    
    @classmethod
    def create(cls, msg_type: str, payload: dict, task_id: Optional[str] = None) -> "Message":
        return cls(
            type=msg_type,
            payload=payload,
            timestamp=int(time.time() * 1000),
            message_id=str(uuid.uuid4()),
            task_id=task_id
        )
    
    def to_dict(self) -> dict:
        return asdict(self)


# 具体消息类型 - 客户端 → 服务端
@dataclass
class TaskStartMessage:
    """开始新任务"""
    user_input: str
    context: Optional[dict] = None


@dataclass
class ThinkingSelectOptionMessage:
    """选择思考选项"""
    node_id: str
    option_id: str


@dataclass
class ExecutionInterveneMessage:
    """执行干预"""
    step_id: str
    intervention_type: str  # replan | skip | stop
    custom_input: Optional[str] = None


# 具体消息类型 - 服务端 → 客户端
@dataclass
class ThinkingNodeCreatedPayload:
    """思考节点创建"""
    node: dict
    options: List[dict]
    allow_custom: bool


@dataclass
class ExecutionBlueprintPayload:
    """执行蓝图加载"""
    blueprint_id: str
    steps: List[dict]


@dataclass
class ExecutionStepUpdatePayload:
    """执行步骤更新"""
    step_id: str
    step_name: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
