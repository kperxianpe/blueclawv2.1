# -*- coding: utf-8 -*-
import pytest

from blueclaw.adapter.ide.planner import ArchitecturePlanner
from blueclaw.adapter.ide.models import CodebaseAnalysis, FileAnalysis, DependencyEdge
from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription


@pytest.fixture
def planner():
    return ArchitecturePlanner()


@pytest.fixture
def sample_analysis():
    return CodebaseAnalysis(
        project_path="/tmp/project",
        files=[
            FileAnalysis(path="src/auth/login.py", language="python", imports=["utils.logger"]),
            FileAnalysis(path="src/utils/logger.py", language="python", imports=[]),
            FileAnalysis(path="src/app.py", language="python", imports=["auth.login"]),
        ],
        dependencies=[
            DependencyEdge(source="src/auth/login.py", target="logger", edge_type="import"),
            DependencyEdge(source="src/app.py", target="login", edge_type="import"),
        ],
    )


def test_plan_generates_tasks(planner, sample_analysis):
    bp = ExecutionBlueprint(
        task_id="bp-1",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="s1", name="Edit login",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="src/auth/login.py")),
            ),
        ],
    )
    plan = planner.plan(bp, sample_analysis)
    assert len(plan.tasks) >= 1
    assert plan.tasks[0].file_path == "src/auth/login.py"


def test_plan_affected_files(planner, sample_analysis):
    bp = ExecutionBlueprint(
        task_id="bp-1",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="s1", name="Edit login",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="src/auth/login.py")),
            ),
        ],
    )
    plan = planner.plan(bp, sample_analysis)
    assert "src/auth/login.py" in plan.affected_files


def test_plan_execution_order(planner, sample_analysis):
    bp = ExecutionBlueprint(
        task_id="bp-1",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="s1", name="Edit login",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="src/auth/login.py")),
            ),
            ExecutionStep(
                step_id="s2", name="Edit app",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="src/app.py")),
                dependencies=["s1"],
            ),
        ],
    )
    plan = planner.plan(bp, sample_analysis)
    assert len(plan.execution_order) >= 2
    idx_s1 = plan.execution_order.index("s1")
    idx_s2 = plan.execution_order.index("s2")
    assert idx_s1 < idx_s2


def test_plan_conflict_detection(planner, sample_analysis):
    bp = ExecutionBlueprint(
        task_id="bp-1",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="s1", name="Edit login A",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="src/auth/login.py")),
            ),
            ExecutionStep(
                step_id="s2", name="Edit login B",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="src/auth/login.py")),
            ),
        ],
    )
    plan = planner.plan(bp, sample_analysis)
    assert len(plan.conflicts) > 0
    assert "login.py" in plan.conflicts[0]


def test_plan_estimated_duration(planner, sample_analysis):
    bp = ExecutionBlueprint(
        task_id="bp-1",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="s1", name="Edit login",
                action=ActionDefinition(type="edit_file", target=TargetDescription(semantic="src/auth/login.py")),
            ),
        ],
    )
    plan = planner.plan(bp, sample_analysis)
    assert plan.estimated_duration_ms > 0


def test_plan_with_no_target_returns_none_task(planner, sample_analysis):
    bp = ExecutionBlueprint(
        task_id="bp-1",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="s1", name="Run tests",
                action=ActionDefinition(type="execute_command", params={"command": "pytest"}),
            ),
        ],
    )
    plan = planner.plan(bp, sample_analysis)
    # execute_command 没有 file_path 应该不产生 task
    assert all(t.task_type == "command" or t.file_path for t in plan.tasks)
