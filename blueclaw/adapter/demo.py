# -*- coding: utf-8 -*-
"""
Week 22 最小端到端 Demo
验证 AdapterManager 路由、生命周期、状态机、错误处理闭环。
"""
import asyncio
from blueclaw.adapter.manager import AdapterManager
from blueclaw.adapter.models import (
    ExecutionBlueprint,
    ExecutionStep,
    ActionDefinition,
    TargetDescription,
    AdapterConfig,
)
from blueclaw.adapter.state import AdapterState
from blueclaw.adapter.exceptions import AdapterException


async def main():
    print("=" * 60)
    print("Week 22 Adapter 最小端到端 Demo")
    print("=" * 60)

    # Demo 1: Manager 路由测试
    blueprint_web = ExecutionBlueprint(
        task_id="demo-web-001",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="s1",
                name="Navigate",
                action=ActionDefinition(
                    type="navigate",
                    target=TargetDescription(semantic="home")
                ),
            ),
        ],
        config=AdapterConfig(headless=True),
    )

    manager = AdapterManager()
    adapter = manager.get_adapter(blueprint_web.adapter_type)
    assert adapter.type == "web"
    print("[PASS] Demo 1: 路由到 WebAdapter")

    # Demo 2: 正常生命周期（execute）
    result = await manager.execute(blueprint_web)
    assert result.success is True
    sm = manager._state_machines["demo-web-001"]
    assert sm.current == AdapterState.COMPLETED
    print(f"[PASS] Demo 2: 执行完成，状态={sm.current.value}，耗时={result.duration_ms:.1f}ms")

    # Demo 3: 暂停 / 恢复
    blueprint_web2 = ExecutionBlueprint(
        task_id="demo-web-002",
        adapter_type="web",
        steps=[ExecutionStep(step_id="s1", name="Wait", action=ActionDefinition(type="wait"))],
    )
    # 手动推进到 EXECUTING 状态以测试 pause/resume
    sm2 = manager._get_or_create_state_machine("demo-web-002")
    await sm2.transition(AdapterState.PLANNING)
    await sm2.transition(AdapterState.EXECUTING)
    await manager.pause("demo-web-002")
    assert sm2.current == AdapterState.PAUSED
    print("[PASS] Demo 3a: 暂停后状态=paused")

    await manager.resume("demo-web-002")
    assert sm2.current == AdapterState.EXECUTING
    print("[PASS] Demo 3b: 恢复后状态=executing")

    # Demo 4: 错误处理（无效适配器类型 + 异常上下文）
    try:
        manager.get_adapter("mobile")
    except ValueError as e:
        assert "Unsupported adapter type" in str(e)
        print("[PASS] Demo 4a: 非法适配器类型捕获成功")

    from blueclaw.adapter.exceptions import ExecutionAdapterException
    try:
        raise ExecutionAdapterException(
            "Mock execution failure",
            context={"blueprint_id": "demo-bad", "adapter_type": "web"}
        )
    except AdapterException as e:
        assert e.category in ["validation", "execution"]
        assert e.context["blueprint_id"] is not None
        print("[PASS] Demo 4b: AdapterException 上下文捕获成功")

    # Demo 5: Core 层转换
    core_bp = {
        "task_id": "demo-core-001",
        "adapter_type": "ide",
        "steps": [
            {
                "step_id": "s1",
                "name": "Open File",
                "action": {"type": "open_file", "target": {"semantic": "main.py"}},
                "dependencies": [],
            }
        ],
        "config": {"headless": False},
    }
    adapter_bp = AdapterManager.from_core_blueprint(core_bp)
    assert adapter_bp.adapter_type == "ide"
    print("[PASS] Demo 5: Core Blueprint 转换成功")

    print("=" * 60)
    print("全部 Demo 通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
