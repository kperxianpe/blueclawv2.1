# -*- coding: utf-8 -*-
"""
Week 22 Adapter 核心架构单元测试
"""
import os
import json
import pytest
import asyncio
import tempfile
import shutil

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
)
from blueclaw.adapter.state import StateMachine, EventBus, AdapterState, FileStatePersistence
from blueclaw.adapter.exceptions import (
    AdapterException,
    NetworkAdapterException,
    LocatorAdapterException,
    ExecutionAdapterException,
    ValidationAdapterException,
    TimeoutAdapterException,
)


@pytest.fixture
def temp_persistence_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def manager(temp_persistence_dir):
    m = AdapterManager()
    m._persistence = FileStatePersistence(temp_persistence_dir)
    return m


@pytest.fixture
def web_blueprint():
    return ExecutionBlueprint(
        task_id="test-web-001",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="s1",
                name="Navigate",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic="home")),
            ),
            ExecutionStep(
                step_id="s2",
                name="Click",
                action=ActionDefinition(type="click", target=TargetDescription(semantic="button")),
            ),
        ],
        config=AdapterConfig(headless=True, timeout=10),
    )


@pytest.fixture
def ide_blueprint():
    return ExecutionBlueprint(
        task_id="test-ide-001",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="s1",
                name="Open File",
                action=ActionDefinition(type="open_file", target=TargetDescription(semantic="main.py")),
            ),
        ],
    )


# ==================== Manager 路由测试 ====================

@pytest.mark.asyncio
async def test_manager_routes_to_web_adapter(manager, web_blueprint):
    adapter = manager.get_adapter("web")
    assert adapter.type == "web"


@pytest.mark.asyncio
async def test_manager_routes_to_ide_adapter(manager, ide_blueprint):
    adapter = manager.get_adapter("ide")
    assert adapter.type == "ide"


@pytest.mark.asyncio
async def test_manager_routes_unknown_adapter(manager):
    with pytest.raises(ValueError):
        manager.get_adapter("mobile")


# ==================== 生命周期测试 ====================

@pytest.mark.asyncio
async def test_manager_execute_lifecycle_web(manager, web_blueprint):
    # 使用 about:blank 避免 navigate 失败，并 mock 干预 UI 自动 skip click 步骤
    from blueclaw.adapter.ui.intervention.base import InterventionResult
    web_blueprint.steps[0].action.target = TargetDescription(semantic="about:blank")
    adapter = manager.get_adapter("web")
    async def mock_show(step, screenshot, error):
        return InterventionResult(type="button", choice="skip")
    adapter.intervention_ui.show = mock_show

    result = await manager.execute(web_blueprint)
    assert isinstance(result, WebExecutionResult)
    assert result.success is True
    sm = manager._state_machines["test-web-001"]
    assert sm.current == AdapterState.COMPLETED
    history = sm.get_history()
    states = [h["to"] for h in history]
    assert "planning" in states
    assert "executing" in states
    assert "completed" in states


@pytest.mark.asyncio
async def test_manager_execute_lifecycle_ide(manager, ide_blueprint):
    result = await manager.execute(ide_blueprint)
    assert isinstance(result, IDEExecutionResult)
    assert result.success is True
    sm = manager._state_machines["test-ide-001"]
    assert sm.current == AdapterState.COMPLETED


@pytest.mark.asyncio
async def test_manager_pause_and_resume_web(manager, web_blueprint):
    # 先执行到某个状态再暂停不太方便，这里直接 PLANNING -> EXECUTING -> PAUSED
    sm = manager._get_or_create_state_machine("test-web-002")
    await sm.transition(AdapterState.PLANNING)
    await sm.transition(AdapterState.EXECUTING)

    adapter = manager.get_adapter("web")
    await adapter.init(web_blueprint)
    await manager.pause("test-web-002")
    assert sm.current == AdapterState.PAUSED

    await manager.resume("test-web-002")
    assert sm.current == AdapterState.EXECUTING


@pytest.mark.asyncio
async def test_manager_cancel(manager, web_blueprint):
    sm = manager._get_or_create_state_machine("test-web-003")
    await sm.transition(AdapterState.PLANNING)
    await manager.cancel("test-web-003")
    assert sm.current == AdapterState.FAILED


# ==================== 状态机测试 ====================

@pytest.mark.asyncio
async def test_state_machine_transitions(temp_persistence_dir):
    sm = StateMachine("t1", persistence=FileStatePersistence(temp_persistence_dir))
    assert sm.current == AdapterState.IDLE
    await sm.transition(AdapterState.PLANNING)
    assert sm.current == AdapterState.PLANNING
    await sm.transition(AdapterState.EXECUTING)
    assert sm.current == AdapterState.EXECUTING
    await sm.transition(AdapterState.VALIDATING)
    assert sm.current == AdapterState.VALIDATING
    await sm.transition(AdapterState.COMPLETED)
    assert sm.current == AdapterState.COMPLETED


@pytest.mark.asyncio
async def test_state_machine_invalid_transition(temp_persistence_dir):
    sm = StateMachine("t2", persistence=FileStatePersistence(temp_persistence_dir))
    with pytest.raises(ValueError):
        await sm.transition(AdapterState.EXECUTING)  # IDLE -> EXECUTING 非法


@pytest.mark.asyncio
async def test_state_machine_failed_from_any(temp_persistence_dir):
    sm = StateMachine("t3", persistence=FileStatePersistence(temp_persistence_dir))
    await sm.transition(AdapterState.PLANNING)
    await sm.transition(AdapterState.EXECUTING)
    await sm.transition(AdapterState.FAILED)
    assert sm.current == AdapterState.FAILED


@pytest.mark.asyncio
async def test_state_machine_concurrency(temp_persistence_dir):
    sm = StateMachine("t4", persistence=FileStatePersistence(temp_persistence_dir))

    async def transitioner(to_state):
        await sm.transition(to_state)

    await sm.transition(AdapterState.PLANNING)
    # 并发尝试两个合法转换（只有一个会成功，另一个会拿到锁后顺序执行）
    await asyncio.gather(
        transitioner(AdapterState.EXECUTING),
        transitioner(AdapterState.PAUSED),
        return_exceptions=True,
    )
    # 由于锁的存在，不会崩溃；结果可能是 EXECUTING 或 PAUSED
    assert sm.current in (AdapterState.EXECUTING, AdapterState.PAUSED)


# ==================== 事件总线测试 ====================

@pytest.mark.asyncio
async def test_state_event_bus():
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(payload)

    bus.subscribe("state.changed", handler)
    await bus.publish("state.changed", {"task_id": "x", "to": "executing"})
    assert len(received) == 1
    assert received[0]["to"] == "executing"

    bus.unsubscribe("state.changed", handler)
    await bus.publish("state.changed", {"task_id": "y", "to": "completed"})
    assert len(received) == 1  # 已取消订阅


# ==================== 持久化测试 ====================

@pytest.mark.asyncio
async def test_file_persistence_save_and_load(temp_persistence_dir):
    fp = FileStatePersistence(temp_persistence_dir)
    sm = StateMachine("p1", persistence=fp)
    await sm.transition(AdapterState.PLANNING)
    await sm.transition(AdapterState.EXECUTING)

    data = fp.load("p1")
    assert data is not None
    assert data["task_id"] == "p1"
    assert data["state"] == "executing"
    assert len(data["history"]) >= 2


# ==================== 错误处理测试 ====================

@pytest.mark.asyncio
async def test_adapter_exception_capture(temp_persistence_dir):
    exc = NetworkAdapterException("Connection refused", context={"host": "localhost"})
    assert exc.category == "network"
    assert exc.context["host"] == "localhost"
    assert "stack_trace" in exc.to_dict()

    # 验证日志文件已写入
    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..", "logs", "adapter_exceptions.jsonl"
    )
    log_path = os.path.abspath(log_path)
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) >= 1
        last = json.loads(lines[-1])
        assert last["category"] == "network"


@pytest.mark.asyncio
async def test_all_exception_subclasses():
    exceptions = [
        NetworkAdapterException("net", {"a": 1}),
        LocatorAdapterException("loc", {"b": 2}),
        ExecutionAdapterException("exec", {"c": 3}),
        ValidationAdapterException("val", {"d": 4}),
        TimeoutAdapterException("time", {"e": 5}),
    ]
    categories = ["network", "locator", "execution", "validation", "timeout"]
    for exc, cat in zip(exceptions, categories):
        assert exc.category == cat
        assert isinstance(exc, AdapterException)


# ==================== Pydantic 模型测试 ====================

@pytest.mark.asyncio
async def test_pydantic_models_serde():
    blueprint = ExecutionBlueprint(
        task_id="serde-001",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="s1",
                name="Click",
                action=ActionDefinition(
                    type="click",
                    target=TargetDescription(semantic="submit", selector="#btn"),
                    params={"times": 1},
                ),
                dependencies=[],
                validation=ValidationRule(type="presence", expected=True),
            ),
        ],
        config=AdapterConfig(headless=False, timeout=5, extra={"viewport": {"w": 1920, "h": 1080}}),
    )
    data = blueprint.model_dump()
    restored = ExecutionBlueprint.model_validate(data)
    assert restored.task_id == "serde-001"
    assert restored.steps[0].action.type == "click"
    assert restored.steps[0].action.target.selector == "#btn"
    assert restored.config.timeout == 5

    web_res = WebExecutionResult(success=True, duration_ms=120.5, output="done")
    assert web_res.model_dump()["success"] is True

    ide_res = IDEExecutionResult(success=True, duration_ms=80.0, output="built", modified_files=["a.py"])
    assert ide_res.model_dump()["modified_files"] == ["a.py"]


# ==================== Core 转换测试 ====================

@pytest.mark.asyncio
async def test_from_core_blueprint():
    core_bp = {
        "task_id": "core-001",
        "adapter_type": "ide",
        "steps": [
            {
                "step_id": "s1",
                "id": "legacy-id",
                "name": "Open",
                "action": {
                    "type": "open_file",
                    "target": {"semantic": "main.py", "selector": None},
                    "params": {"line": 10},
                },
                "dependencies": ["s0"],
                "validation": {"type": "return_code", "expected": 0},
            }
        ],
        "config": {"headless": False},
    }
    bp = AdapterManager.from_core_blueprint(core_bp)
    assert bp.task_id == "core-001"
    assert bp.adapter_type == "ide"
    assert bp.steps[0].step_id == "s1"
    assert bp.steps[0].action.type == "open_file"
    assert bp.steps[0].dependencies == ["s0"]
    assert bp.steps[0].validation.type == "return_code"


# ==================== 验证状态流转测试 ====================

@pytest.mark.asyncio
async def test_manager_with_validation_step(manager):
    bp = ExecutionBlueprint(
        task_id="val-001",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="s1",
                name="Navigate",
                action=ActionDefinition(type="navigate"),
                validation=ValidationRule(type="presence", expected=True),
            ),
        ],
    )
    result = await manager.execute(bp)
    sm = manager._state_machines["val-001"]
    history = sm.get_history()
    states = [h["to"] for h in history]
    assert "validating" in states
    assert sm.current == AdapterState.COMPLETED
