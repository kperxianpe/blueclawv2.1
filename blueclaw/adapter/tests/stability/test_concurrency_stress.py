# -*- coding: utf-8 -*-
"""
稳定性测试 - 并发压力

- 多任务并发分析
- 状态机并发访问
- 并行执行器高负载
"""
import asyncio
import pytest

from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.web.parallel import ParallelExecutor
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.state import StateMachine, AdapterState


def test_parallel_executor_high_load():
    """并行执行器处理大量步骤"""
    steps = [
        ExecutionStep(
            step_id=f"step_{i}",
            name=f"Step {i}",
            action=ActionDefinition(type="wait", target=TargetDescription(semantic=""), params={"ms": 10}),
            dependencies=[],
        )
        for i in range(20)
    ]

    blueprint = ExecutionBlueprint(
        task_id="stress_parallel",
        adapter_type="web",
        steps=steps,
    )

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=5,
    )

    analysis = executor.analyze_parallel_potential(blueprint)
    assert analysis["total_steps"] == 20
    assert analysis["levels"] == 1  # 全部无依赖，1 层
    assert analysis["max_parallel_per_level"] == 20


@pytest.mark.asyncio
async def test_state_machine_concurrent_transitions():
    """状态机并发转换安全"""
    sm = StateMachine(task_id="concurrent_test")

    async def transition_task(target_state):
        try:
            await sm.transition(target_state, {"action": "test"})
            return True
        except Exception:
            return False

    # 从 IDLE 并发尝试转换到不同状态
    results = await asyncio.gather(
        transition_task(AdapterState.PLANNING),
        transition_task(AdapterState.PLANNING),
        transition_task(AdapterState.PLANNING),
    )

    # 至少一个成功
    assert any(results)
    # 最终状态是 PLANNING
    assert sm.current == AdapterState.PLANNING


def test_dependency_graph_100_steps():
    """100 步骤的依赖图分析性能"""
    steps = [
        ExecutionStep(
            step_id=f"s{i}",
            name=f"S{i}",
            action=ActionDefinition(type="wait", target=TargetDescription(semantic="")),
            dependencies=[f"s{i - 1}"] if i > 0 else [],
        )
        for i in range(100)
    ]

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=10,
    )

    graph = executor._build_dependency_graph(steps)
    levels = executor._group_by_levels(steps, graph)

    assert len(levels) == 100  # 线性依赖，100 层
    assert all(len(level) == 1 for level in levels)


def test_parallel_analysis_50_steps():
    """50 步骤的并行分析"""
    steps = [
        ExecutionStep(
            step_id=f"s{i}",
            name=f"S{i}",
            action=ActionDefinition(type="wait", target=TargetDescription(semantic="")),
            dependencies=[],
        )
        for i in range(50)
    ]

    blueprint = ExecutionBlueprint(task_id="stress_50", adapter_type="web", steps=steps)
    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=10,
    )

    analysis = executor.analyze_parallel_potential(blueprint)
    assert analysis["total_steps"] == 50
    assert analysis["max_parallel_per_level"] == 50
