# -*- coding: utf-8 -*-
"""
ParallelExecutor 单元测试
"""
import pytest

from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.web.parallel import ParallelExecutor
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot


@pytest.fixture
def parallel_executor():
    return ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=3,
    )


def test_build_dependency_graph(parallel_executor):
    """测试依赖图构建"""
    steps = [
        ExecutionStep(step_id="a", name="A", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=[]),
        ExecutionStep(step_id="b", name="B", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["a"]),
        ExecutionStep(step_id="c", name="C", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["a"]),
    ]
    graph = parallel_executor._build_dependency_graph(steps)
    assert graph["b"] == {"a"}
    assert graph["c"] == {"a"}
    assert "a" not in graph or graph["a"] == set()


def test_group_by_levels_linear(parallel_executor):
    """测试线性依赖的层级分组"""
    steps = [
        ExecutionStep(step_id="a", name="A", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=[]),
        ExecutionStep(step_id="b", name="B", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["a"]),
        ExecutionStep(step_id="c", name="C", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["b"]),
    ]
    graph = parallel_executor._build_dependency_graph(steps)
    levels = parallel_executor._group_by_levels(steps, graph)

    assert len(levels) == 3
    assert [s.step_id for s in levels[0]] == ["a"]
    assert [s.step_id for s in levels[1]] == ["b"]
    assert [s.step_id for s in levels[2]] == ["c"]


def test_group_by_levels_parallel(parallel_executor):
    """测试并行步骤的层级分组"""
    steps = [
        ExecutionStep(step_id="a", name="A", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=[]),
        ExecutionStep(step_id="b", name="B", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=[]),
        ExecutionStep(step_id="c", name="C", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["a", "b"]),
    ]
    graph = parallel_executor._build_dependency_graph(steps)
    levels = parallel_executor._group_by_levels(steps, graph)

    assert len(levels) == 2
    assert set(s.step_id for s in levels[0]) == {"a", "b"}
    assert [s.step_id for s in levels[1]] == ["c"]


def test_group_by_levels_with_missing_deps(parallel_executor):
    """测试包含不存在依赖的层级分组"""
    steps = [
        ExecutionStep(step_id="a", name="A", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=[]),
        ExecutionStep(step_id="b", name="B", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["a", "nonexistent"]),
    ]
    graph = parallel_executor._build_dependency_graph(steps)
    levels = parallel_executor._group_by_levels(steps, graph)

    # nonexistent 不在 steps 中，所以 b 的依赖只有 a
    assert len(levels) == 2
    assert [s.step_id for s in levels[0]] == ["a"]
    assert [s.step_id for s in levels[1]] == ["b"]


def test_analyze_parallel_potential(parallel_executor):
    """测试并行潜力分析"""
    blueprint = ExecutionBlueprint(
        task_id="test_parallel",
        adapter_type="web",
        steps=[
            ExecutionStep(step_id="a", name="A", action=ActionDefinition(type="wait", target=TargetDescription(semantic=""), params={"estimated_duration_ms": 1000}), dependencies=[]),
            ExecutionStep(step_id="b", name="B", action=ActionDefinition(type="wait", target=TargetDescription(semantic=""), params={"estimated_duration_ms": 2000}), dependencies=["a"]),
            ExecutionStep(step_id="c", name="C", action=ActionDefinition(type="wait", target=TargetDescription(semantic=""), params={"estimated_duration_ms": 1500}), dependencies=["a"]),
            ExecutionStep(step_id="d", name="D", action=ActionDefinition(type="wait", target=TargetDescription(semantic=""), params={"estimated_duration_ms": 1000}), dependencies=["b", "c"]),
        ],
    )

    analysis = parallel_executor.analyze_parallel_potential(blueprint)
    assert analysis["total_steps"] == 4
    assert analysis["levels"] == 3
    assert analysis["max_parallel_per_level"] == 2  # b 和 c 并行
    assert analysis["speedup_estimate"] > 1.0
    assert len(analysis["level_breakdown"]) == 3


def test_analyze_parallel_potential_no_steps(parallel_executor):
    """测试空蓝图的并行分析"""
    blueprint = ExecutionBlueprint(task_id="empty", adapter_type="web", steps=[])
    analysis = parallel_executor.analyze_parallel_potential(blueprint)
    assert analysis["total_steps"] == 0
    assert analysis["levels"] == 0
    assert analysis["speedup_estimate"] == 1.0


def test_semaphore_concurrency_limit(parallel_executor):
    """测试信号量限制并发数"""
    assert parallel_executor.max_concurrency == 3
    assert parallel_executor._semaphore._value == 3
