# -*- coding: utf-8 -*-
"""
集成测试 - 全流程

- 用户输入 -> 蓝图生成 -> 执行 -> 结果输出
- 干预流程完整测试
- 检查点恢复流程
"""
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.models import (
    ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription,
    StepResult,
)
from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
from blueclaw.adapter.ide.planner import ArchitecturePlanner
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.models import SandboxConfig
from blueclaw.adapter.state import StateMachine, AdapterState


@pytest.fixture
def sample_project():
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "main.py"), "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.asyncio
async def test_full_ide_pipeline(sample_project):
    """完整 IDE 流水线：分析 -> 规划 -> LLM -> 沙盒 -> 应用"""
    # 1. 分析
    analyzer = CodebaseAnalyzer(sample_project)
    analysis = analyzer.analyze()
    assert analysis.total_files >= 1

    # 2. 规划
    planner = ArchitecturePlanner()
    blueprint = ExecutionBlueprint(
        task_id="full_pipeline",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="add_type_hint",
                name="Add type hint",
                action=ActionDefinition(
                    type="edit_file",
                    target=TargetDescription(semantic="main.py"),
                    params={"estimated_lines": 2},
                ),
            ),
        ],
    )
    plan = planner.plan(blueprint, analysis)
    assert len(plan.tasks) >= 1

    # 3. Mock LLM
    diff_text = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,2 @@
-def add(a, b):
+def add(a: int, b: int) -> int:
     return a + b
"""
    code_model = MockCodeModelClient(response_template=diff_text)
    response = await code_model.generate_code_changes(
        task_description="Add type hints",
        file_context={"main.py": open(os.path.join(sample_project, "main.py")).read()},
    )
    assert response.success is True
    assert len(response.diffs) == 1

    # 4. 沙盒验证
    sandbox = SandboxValidator(sample_project, config=SandboxConfig(check_tests=False))
    validation = await sandbox.validate(response.diffs)
    assert validation.success is True

    # 5. 应用
    applier = IncrementApplier(sample_project)
    apply_result = applier.apply_diffs(response.diffs, auto_commit=False)
    assert apply_result.success is True

    # 验证文件内容
    with open(os.path.join(sample_project, "main.py"), "r") as f:
        content = f.read()
    assert "int" in content


def test_full_state_machine_lifecycle():
    """完整状态机生命周期"""
    sm = StateMachine(task_id="lifecycle_test")
    assert sm.current == AdapterState.IDLE

    # 正常流程
    import asyncio
    asyncio.run(sm.transition(AdapterState.PLANNING, {"action": "init"}))
    asyncio.run(sm.transition(AdapterState.EXECUTING, {"action": "execute"}))
    asyncio.run(sm.transition(AdapterState.COMPLETED, {"action": "finish"}))

    assert sm.current == AdapterState.COMPLETED
    assert len(sm.get_history()) == 3


@pytest.mark.asyncio
async def test_intervention_pause_resume_flow():
    """干预暂停/恢复流程"""
    sm = StateMachine(task_id="intervention_test")

    await sm.transition(AdapterState.PLANNING, {"action": "init"})
    await sm.transition(AdapterState.EXECUTING, {"action": "execute"})
    assert sm.current == AdapterState.EXECUTING

    await sm.transition(AdapterState.PAUSED, {"action": "pause", "reason": "user_request"})
    assert sm.current == AdapterState.PAUSED

    await sm.transition(AdapterState.EXECUTING, {"action": "resume"})
    assert sm.current == AdapterState.EXECUTING

    await sm.transition(AdapterState.COMPLETED, {"action": "finish"})
    assert sm.current == AdapterState.COMPLETED


def test_step_result_serialization():
    """StepResult 序列化和反序列化"""
    result = StepResult(
        status="success",
        output="done",
        error=None,
        duration_ms=1500.5,
        needs_intervention=False,
    )

    data = result.model_dump()
    assert data["status"] == "success"
    assert data["output"] == "done"
    assert data["duration_ms"] == 1500.5

    restored = StepResult(**data)
    assert restored.status == result.status
    assert restored.duration_ms == result.duration_ms
