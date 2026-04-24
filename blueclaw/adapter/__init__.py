# -*- coding: utf-8 -*-
"""
Blueclaw Adapter 执行适配层 (Week 22)

将 Core 引擎生成的 ExecutionBlueprint 路由到外部目标环境（Web 浏览器、IDE 编辑器）。
与 backend/adapter/（元工具层）相互独立。
"""

from blueclaw.adapter.manager import AdapterManager
from blueclaw.adapter.models import (
    ExecutionBlueprint,
    ExecutionStep,
    ActionDefinition,
    TargetDescription,
    ValidationRule,
    AdapterConfig,
    WebExecutionResult,
    IDEExecutionResult,
    StepResult,
)
from blueclaw.adapter.exceptions import AdapterException
from blueclaw.adapter.state import StateMachine, EventBus, AdapterState
from blueclaw.adapter.core.operation_record import OperationRecord, OperationLog
from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2
from blueclaw.adapter.core.replan_engine import AdapterReplanEngine
from blueclaw.adapter.ui.intervention.base import InterventionUI, InterventionResult

__all__ = [
    "AdapterManager",
    "ExecutionBlueprint",
    "ExecutionStep",
    "ActionDefinition",
    "TargetDescription",
    "ValidationRule",
    "AdapterConfig",
    "WebExecutionResult",
    "IDEExecutionResult",
    "StepResult",
    "AdapterException",
    "StateMachine",
    "EventBus",
    "AdapterState",
    "OperationRecord",
    "OperationLog",
    "CheckpointManagerV2",
    "AdapterReplanEngine",
    "InterventionUI",
    "InterventionResult",
]
