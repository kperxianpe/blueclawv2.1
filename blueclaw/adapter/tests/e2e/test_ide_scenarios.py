# -*- coding: utf-8 -*-
"""
E2E IDE 场景测试

- 代码分析和符号提取
- 修改计划生成
- Mock 代码模型生成 diff
- 沙盒验证
- 增量应用
"""
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
from blueclaw.adapter.ide.planner import ArchitecturePlanner
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.models import SandboxConfig
from blueclaw.adapter.models import (
    ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription,
)


@pytest.fixture
def sample_python_project():
    """创建一个示例 Python 项目"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "main.py"), "w") as f:
            f.write("""def greet(name):
    return f"Hello, {name}!"

def add(a, b):
    return a + b
""")
        with open(os.path.join(path, "utils.py"), "w") as f:
            f.write("""def helper():
    return 42
""")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def buggy_project():
    """创建一个有 bug 的项目"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "math_ops.py"), "w") as f:
            f.write("""def divide(a, b):
    return a / b
""")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_e2e_analyze_and_plan(sample_python_project):
    """端到端：分析代码并生成修改计划"""
    analyzer = CodebaseAnalyzer(sample_python_project)
    analysis = analyzer.analyze()

    assert analysis.total_files == 2
    assert "python" in analysis.languages

    planner = ArchitecturePlanner()
    blueprint = ExecutionBlueprint(
        task_id="e2e_refactor",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="add_type_hints",
                name="Add type hints to main.py",
                action=ActionDefinition(
                    type="edit_file",
                    target=TargetDescription(semantic="main.py"),
                    params={"estimated_lines": 4},
                ),
            ),
        ],
    )
    plan = planner.plan(blueprint, analysis)
    assert len(plan.tasks) >= 1
    assert "main.py" in plan.affected_files


@pytest.mark.asyncio
async def test_e2e_mock_llm_and_sandbox(sample_python_project):
    """端到端：Mock LLM 生成 diff -> 沙盒验证"""
    diff_text = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,2 @@
-def greet(name):
+def greet(name: str) -> str:
     return f"Hello, {name}!"
"""
    code_model = MockCodeModelClient(response_template=diff_text)
    response = await code_model.generate_code_changes(
        task_description="Add type hints",
        file_context={"main.py": open(os.path.join(sample_python_project, "main.py")).read()},
    )
    assert response.success is True
    assert len(response.diffs) == 1

    # 沙盒验证
    sandbox = SandboxValidator(
        sample_python_project,
        config=SandboxConfig(check_tests=False),
    )
    validation = await sandbox.validate(response.diffs)
    assert validation.success is True
    assert validation.checks[0].passed is True


@pytest.mark.asyncio
async def test_e2e_bugfix_pipeline(buggy_project):
    """端到端：Bug 修复完整流水线"""
    # 1. 分析
    analyzer = CodebaseAnalyzer(buggy_project)
    analysis = analyzer.analyze()

    # 2. 规划
    planner = ArchitecturePlanner()
    blueprint = ExecutionBlueprint(
        task_id="e2e_fix_divzero",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="fix_divide",
                name="Fix divide by zero",
                action=ActionDefinition(
                    type="edit_file",
                    target=TargetDescription(semantic="math_ops.py"),
                    params={"estimated_lines": 3},
                ),
            ),
        ],
    )
    plan = planner.plan(blueprint, analysis)

    # 3. Mock LLM
    diff_text = """diff --git a/math_ops.py b/math_ops.py
--- a/math_ops.py
+++ b/math_ops.py
@@ -1,2 +1,4 @@
 def divide(a, b):
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
     return a / b
"""
    code_model = MockCodeModelClient(response_template=diff_text)
    response = await code_model.generate_code_changes(
        task_description="Fix divide by zero",
        file_context={"math_ops.py": open(os.path.join(buggy_project, "math_ops.py")).read()},
    )

    # 4. 沙盒验证
    sandbox = SandboxValidator(buggy_project, config=SandboxConfig(check_tests=False))
    validation = await sandbox.validate(response.diffs)

    # 5. 应用
    applier = IncrementApplier(buggy_project)
    apply_result = applier.apply_diffs(response.diffs, auto_commit=False)

    # 验证
    assert validation.success is True
    assert apply_result.success is True
    with open(os.path.join(buggy_project, "math_ops.py"), "r") as f:
        content = f.read()
    assert "ValueError" in content


def test_e2e_symbol_extraction(sample_python_project):
    """端到端：符号提取和依赖分析"""
    analyzer = CodebaseAnalyzer(sample_python_project)
    analysis = analyzer.analyze()

    symbol_map = analyzer.get_symbol_map(analysis)
    assert "main.py" in symbol_map
    names = {s.name for s in symbol_map["main.py"]}
    assert "greet" in names
    assert "add" in names

    # 检查行数统计
    assert analysis.total_lines >= 5
