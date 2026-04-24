# -*- coding: utf-8 -*-
"""
Week 22 核心架构验收测试（对应用户验收文档）
"""
import asyncio
import json
import pytest
from pydantic import ValidationError as PydanticValidationError

from blueclaw.adapter.manager import AdapterManager
from blueclaw.adapter.models import (
    ExecutionBlueprint,
    ExecutionStep,
    ActionDefinition,
    TargetDescription,
    CanvasMindMessage,
    InterventionEvent,
)
from blueclaw.adapter.state import StateMachine, AdapterState
from blueclaw.adapter.exceptions import ValidationAdapterException


# ==================== 测试 1：AdapterManager 路由 ====================
@pytest.mark.asyncio
async def test_1_adapter_manager_routing():
    blueprint = {
        "task_id": "task-001",
        "adapter_type": "web",
        "steps": [{"step_id": "s1", "action": {"type": "navigate", "target": {"semantic": "test"}}}],
        "config": {"headless": True},
    }
    manager = AdapterManager()
    adapter = manager.get_adapter(blueprint["adapter_type"])
    assert adapter.type == "web"
    assert hasattr(adapter, "execute")
    assert hasattr(adapter, "pause")
    assert hasattr(adapter, "resume")


# ==================== 测试 2：数据模型序列化与验证 ====================
@pytest.mark.asyncio
async def test_2_model_serde():
    json_str = json.dumps({
        "task_id": "task-002",
        "adapter_type": "web",
        "steps": [{
            "step_id": "s1",
            "name": "Click",
            "action": {
                "type": "click",
                "target": {"semantic": "login button", "selector": "#login"},
                "params": {}
            },
            "dependencies": []
        }],
        "config": {"headless": False, "timeout": 10}
    })

    blueprint = ExecutionBlueprint.model_validate_json(json_str)
    re_parsed = ExecutionBlueprint.model_validate_json(blueprint.model_dump_json())

    assert blueprint.steps[0].action.type == "click"
    assert blueprint.steps[0].action.target.semantic is not None
    assert re_parsed.task_id == blueprint.task_id


# ==================== 测试 3：状态机流转 ====================
@pytest.mark.asyncio
async def test_3_state_machine_transitions():
    sm = StateMachine("task-003")
    assert sm.current == AdapterState.IDLE

    # 正常流转
    await sm.start_execution()
    assert sm.current == AdapterState.EXECUTING
    await sm.pause()
    assert sm.current == AdapterState.PAUSED
    await sm.resume()
    assert sm.current == AdapterState.EXECUTING
    await sm.complete()
    assert sm.current == AdapterState.COMPLETED

    # 非法操作：COMPLETED -> start_execution 不合法
    with pytest.raises(ValueError):
        await sm.start_execution()


# ==================== 测试 4：异常处理框架 ====================
@pytest.mark.asyncio
async def test_4_exception_handling():
    # 场景 A：Pydantic 验证失败（缺少必填字段）
    with pytest.raises(PydanticValidationError) as exc_info:
        ExecutionBlueprint.model_validate({"task_id": "bad"})
    # Pydantic ValidationError 包含详细上下文（缺失 adapter_type 或 steps 均可）
    assert "adapter_type" in str(exc_info.value) or "steps" in str(exc_info.value)

    # 场景 B：自定义异常构造
    error = ValidationAdapterException("缺少字段", context={"field": "steps"})
    assert error.category == "validation"
    assert error.context["field"] == "steps"


# ==================== 测试 5：CanvasMind 消息格式 ====================
@pytest.mark.asyncio
async def test_5_canvas_mind_message_format():
    message = {
        "adapterType": "web",
        "taskId": "task-001",
        "currentStep": 2,
        "totalSteps": 5,
        "state": "executing",
        "operation": {"type": "click", "x": 120, "y": 80},
    }
    cm = CanvasMindMessage.model_validate(message)
    assert cm.adapterType == "web"
    assert cm.taskId == "task-001"
    assert cm.currentStep == 2
    assert cm.totalSteps == 5
    assert cm.state == "executing"
    assert cm.operation["type"] == "click"


# ==================== 测试 6：用户干预反馈通道 ====================
@pytest.mark.asyncio
async def test_6_intervention_event_model():
    intervention_event = {
        "task_id": "task-001",
        "checkpoint_seq": 1,
        "type": "text_hint",
        "payload": {"content": "用邮箱登录，别用手机号"},
        "timestamp": 1713240000000,
    }
    event = InterventionEvent.model_validate(intervention_event)
    assert event.task_id == "task-001"
    assert event.checkpoint_seq == 1
    assert event.type == "text_hint"
    assert event.payload["content"] == "用邮箱登录，别用手机号"
    assert event.timestamp == 1713240000000

    # 序列化/反序列化正常
    recovered = InterventionEvent.model_validate_json(event.model_dump_json())
    assert recovered.task_id == event.task_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
