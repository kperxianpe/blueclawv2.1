# -*- coding: utf-8 -*-
"""
集成测试 - Core 层与 Adapter 层

- AdapterManager 路由
- 状态机与执行联动
- 异常传播
"""
import pytest

from blueclaw.adapter.manager import AdapterManager
from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.state import AdapterState
from blueclaw.adapter.exceptions import ExecutionAdapterException


@pytest.fixture
def manager():
    return AdapterManager()


@pytest.fixture
def simple_blueprint():
    return ExecutionBlueprint(
        task_id="integration_test",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="navigate",
                name="Navigate",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic="about:blank")),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_manager_routes_to_web_adapter(manager, simple_blueprint):
    """AdapterManager 正确路由到 Web Adapter"""
    adapter = manager.get_adapter("web")
    assert adapter is not None


@pytest.mark.asyncio
async def test_manager_state_transitions(manager, simple_blueprint):
    """Manager 执行时状态机正确转换"""
    sm = manager._get_or_create_state_machine("integration_test")
    assert sm.current == AdapterState.IDLE

    # 手动模拟状态转换
    await sm.transition(AdapterState.PLANNING, {"action": "init"})
    assert sm.current == AdapterState.PLANNING

    await sm.transition(AdapterState.EXECUTING, {"action": "execute"})
    assert sm.current == AdapterState.EXECUTING


def test_manager_get_adapter_ide(manager):
    """Manager 支持 IDE Adapter"""
    adapter = manager.get_adapter("ide")
    assert adapter is not None


def test_manager_unknown_adapter_raises(manager):
    """未知 Adapter 类型抛出异常"""
    with pytest.raises(ValueError):
        manager.get_adapter("unknown")


@pytest.mark.asyncio
async def test_manager_pause_resume(manager, simple_blueprint):
    """暂停/恢复流程"""
    sm = manager._get_or_create_state_machine("pause_test")
    await sm.transition(AdapterState.PLANNING, {"action": "init"})
    await sm.transition(AdapterState.EXECUTING, {"action": "execute"})

    await manager.pause("pause_test")
    assert sm.current == AdapterState.PAUSED

    await manager.resume("pause_test")
    assert sm.current == AdapterState.EXECUTING


@pytest.mark.asyncio
async def test_state_machine_persistence(manager, simple_blueprint, tmp_path):
    """状态机持久化集成"""
    from blueclaw.adapter.state import FileStatePersistence, AdapterState

    persist = FileStatePersistence()

    sm1 = manager._get_or_create_state_machine("persist_test")
    await sm1.transition(AdapterState.PLANNING, {"action": "init"})
    await sm1.transition(AdapterState.EXECUTING, {"action": "execute"})
    await sm1.transition(AdapterState.COMPLETED, {"action": "finish"})

    persist.save("persist_test", AdapterState.COMPLETED, sm1.get_history())
    loaded = persist.load("persist_test")

    assert loaded is not None
    assert loaded["state"].lower() == "completed"
    assert loaded["task_id"] == "persist_test"
