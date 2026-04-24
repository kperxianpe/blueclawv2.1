# -*- coding: utf-8 -*-
"""
集成测试 - 边界情况

- 空蓝图
- 超长任务列表
- 循环依赖
- 无效参数
"""
import pytest

from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.web.parallel import ParallelExecutor
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
from blueclaw.adapter.ide.planner import ArchitecturePlanner


def test_empty_blueprint():
    """空蓝图处理"""
    blueprint = ExecutionBlueprint(task_id="empty", adapter_type="web", steps=[])
    assert blueprint.task_id == "empty"
    assert len(blueprint.steps) == 0

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=3,
    )
    analysis = executor.analyze_parallel_potential(blueprint)
    assert analysis["total_steps"] == 0
    assert analysis["levels"] == 0


def test_single_step_blueprint():
    """单步骤蓝图"""
    blueprint = ExecutionBlueprint(
        task_id="single",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="only",
                name="Only step",
                action=ActionDefinition(type="wait", target=TargetDescription(semantic="")),
            ),
        ],
    )

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=3,
    )
    analysis = executor.analyze_parallel_potential(blueprint)
    assert analysis["total_steps"] == 1
    assert analysis["levels"] == 1
    assert analysis["speedup_estimate"] == 1.0


def test_circular_dependency_handling():
    """循环依赖处理"""
    steps = [
        ExecutionStep(step_id="a", name="A", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["c"]),
        ExecutionStep(step_id="b", name="B", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["a"]),
        ExecutionStep(step_id="c", name="C", action=ActionDefinition(type="wait", target=TargetDescription(semantic="")), dependencies=["b"]),
    ]

    executor = ParallelExecutor(
        executor=WebExecutor(PlaywrightScreenshot()),
        max_concurrency=3,
    )

    graph = executor._build_dependency_graph(steps)
    levels = executor._group_by_levels(steps, graph)

    # 循环依赖时，应全部放入一层或按某种顺序处理
    assert len(levels) >= 1
    all_grouped = sum(len(l) for l in levels)
    assert all_grouped == 3


def test_long_step_names():
    """超长步骤名称"""
    long_name = "A" * 1000
    step = ExecutionStep(
        step_id="long_name",
        name=long_name,
        action=ActionDefinition(type="wait", target=TargetDescription(semantic="")),
    )
    assert step.name == long_name
    assert len(step.step_id) < 100  # step_id 不长


def test_invalid_adapter_type():
    """无效 adapter 类型"""
    from blueclaw.adapter.manager import AdapterManager
    manager = AdapterManager()
    with pytest.raises(ValueError):
        manager.get_adapter("nonexistent")


def test_analyzer_empty_project():
    """分析空项目"""
    import tempfile
    import shutil
    path = tempfile.mkdtemp()
    try:
        analyzer = CodebaseAnalyzer(path)
        analysis = analyzer.analyze()
        assert analysis.total_files == 0
        assert analysis.total_lines == 0
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_planner_no_analysis():
    """规划器处理空分析"""
    planner = ArchitecturePlanner()
    blueprint = ExecutionBlueprint(
        task_id="no_analysis",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="edit",
                name="Edit file",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="nonexistent.py")),
            ),
        ],
    )
    from blueclaw.adapter.ide.models import CodebaseAnalysis
    empty_analysis = CodebaseAnalysis(project_path="/tmp/empty")
    plan = planner.plan(blueprint, empty_analysis)
    assert len(plan.tasks) >= 1
    assert plan.conflicts == []
