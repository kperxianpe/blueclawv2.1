# -*- coding: utf-8 -*-
"""
执行性能测试

- 并行执行 vs 串行执行耗时对比
- 单步执行耗时
- 依赖分析耗时
"""
import time
import pytest

from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.web.parallel import ParallelExecutor
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot


def test_parallel_analysis_speed():
    """测试并行分析的速度"""
    blueprint = ExecutionBlueprint(
        task_id="perf_parallel",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id=f"step_{i}",
                name=f"Step {i}",
                action=ActionDefinition(type="wait", target=TargetDescription(semantic=""), params={"ms": 100}),
                dependencies=["step_0"] if i > 0 else [],
            )
            for i in range(5)
        ],
    )

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=3,
    )

    start = time.time()
    analysis = executor.analyze_parallel_potential(blueprint)
    duration = time.time() - start

    print(f"\nParallel analysis: {duration * 1000:.1f}ms")
    print(f"  Levels: {analysis['levels']}")
    print(f"  Max parallel: {analysis['max_parallel_per_level']}")
    print(f"  Speedup estimate: {analysis['speedup_estimate']:.2f}x")

    assert analysis["total_steps"] == 5
    assert duration < 0.1  # 分析应很快


def test_dependency_graph_construction():
    """测试依赖图构建性能（大量步骤）"""
    steps = [
        ExecutionStep(
            step_id=f"step_{i}",
            name=f"Step {i}",
            action=ActionDefinition(type="wait", target=TargetDescription(semantic="")),
            dependencies=[f"step_{i - 1}"] if i > 0 else [],
        )
        for i in range(100)
    ]

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=5,
    )

    start = time.time()
    graph = executor._build_dependency_graph(steps)
    duration = time.time() - start

    print(f"\nDependency graph (100 steps): {duration * 1000:.1f}ms")
    assert len(graph) == 99  # step_0 没有依赖
    assert duration < 0.1


def test_level_grouping_performance():
    """测试层级分组性能"""
    # 创建星型依赖：中心节点 -> 10 个并行叶子节点
    steps = [
        ExecutionStep(
            step_id="center",
            name="Center",
            action=ActionDefinition(type="wait", target=TargetDescription(semantic="")),
            dependencies=[],
        ),
    ]
    for i in range(10):
        steps.append(ExecutionStep(
            step_id=f"leaf_{i}",
            name=f"Leaf {i}",
            action=ActionDefinition(type="wait", target=TargetDescription(semantic="")),
            dependencies=["center"],
        ))

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=5,
    )

    graph = executor._build_dependency_graph(steps)

    start = time.time()
    levels = executor._group_by_levels(steps, graph)
    duration = time.time() - start

    print(f"\nLevel grouping (11 steps, star): {duration * 1000:.1f}ms")
    assert len(levels) == 2  # 2 层：中心 + 叶子
    assert len(levels[0]) == 1  # 中心
    assert len(levels[1]) == 10  # 10 个叶子
    assert duration < 0.1


def test_complex_dependency_grouping():
    """测试复杂依赖的层级分组"""
    # DAG: A -> B -> D, A -> C -> D
    steps = [
        ExecutionStep(step_id="A", name="A", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=[]),
        ExecutionStep(step_id="B", name="B", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["A"]),
        ExecutionStep(step_id="C", name="C", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["A"]),
        ExecutionStep(step_id="D", name="D", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["B", "C"]),
    ]

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=3,
    )

    graph = executor._build_dependency_graph(steps)
    levels = executor._group_by_levels(steps, graph)

    print(f"\nComplex DAG levels: {[[s.step_id for s in level] for level in levels]}")
    assert len(levels) == 3
    assert [s.step_id for s in levels[0]] == ["A"]
    assert set(s.step_id for s in levels[1]) == {"B", "C"}
    assert [s.step_id for s in levels[2]] == ["D"]
