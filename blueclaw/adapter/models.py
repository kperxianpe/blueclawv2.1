# -*- coding: utf-8 -*-
"""
Adapter 层数据模型 (Pydantic v2)

定义 Adapter 执行层与 Core 层之间的输入/输出契约。
"""
from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


class AdapterConfig(BaseModel):
    """Adapter 执行配置"""
    headless: bool = True
    timeout: int = Field(default=30, ge=1)
    extra: Dict[str, Any] = Field(default_factory=dict)


class TargetDescription(BaseModel):
    """动作目标描述（语义 + 可选技术定位器）"""
    semantic: str = ""
    selector: Optional[str] = None
    coordinates: Optional[Dict[str, int]] = None


class ActionDefinition(BaseModel):
    """步骤动作定义"""
    type: Literal[
        "navigate", "click", "input", "scroll", "screenshot", "select",
        "execute_command", "open_file", "edit_file", "select_text",
        "wait"
    ]
    target: Optional[TargetDescription] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class ValidationRule(BaseModel):
    """步骤执行后的验证规则"""
    type: Literal["presence", "text_contains", "return_code", "custom", "url_match", "visual_match"]
    expected: Any


class ExecutionStep(BaseModel):
    """Adapter 层执行步骤"""
    step_id: str
    name: str
    action: ActionDefinition
    dependencies: List[str] = Field(default_factory=list)
    validation: Optional[ValidationRule] = None


class ExecutionBlueprint(BaseModel):
    """Adapter 层执行蓝图"""
    task_id: str
    adapter_type: Literal["web", "ide"]
    steps: List[ExecutionStep] = Field(default_factory=list)
    config: AdapterConfig = Field(default_factory=AdapterConfig)


class WebExecutionResult(BaseModel):
    """Web 适配器执行结果"""
    success: bool
    duration_ms: float
    output: str
    screenshot: Optional[str] = None
    error_context: Optional[Dict[str, Any]] = None


class IDEExecutionResult(BaseModel):
    """IDE 适配器执行结果"""
    success: bool
    duration_ms: float
    output: str
    modified_files: List[str] = Field(default_factory=list)
    error_context: Optional[Dict[str, Any]] = None


# CanvasMind 消息格式（WebSocket 状态推送）
class CanvasMindMessage(BaseModel):
    """CanvasMind 状态更新消息"""
    adapterType: Literal["web", "ide"]
    taskId: str
    currentStep: int
    totalSteps: int
    state: Literal["idle", "planning", "executing", "validating", "paused", "completed", "failed"]
    operation: Optional[Dict[str, Any]] = None


# 用户干预事件
class InterventionEvent(BaseModel):
    """用户干预事件"""
    task_id: str
    checkpoint_seq: int
    type: Literal["text_hint", "click_correction", "stop", "replan"]
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[int] = None  # Unix timestamp (ms)


class StepResult(BaseModel):
    """单步骤执行结果"""
    status: Literal["success", "failed", "skipped", "intervention_needed"]
    output: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0
    needs_intervention: bool = False


# 联合返回类型
ExecutionResult = Union[WebExecutionResult, IDEExecutionResult]
