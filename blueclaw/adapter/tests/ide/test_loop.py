# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.ide.loop import ModificationLoop
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.models import (
    LoopConfig, FileDiff, DiffHunk, SandboxConfig,
    SandboxValidationResult, ValidationCheck,
)


@pytest.fixture
def loop_fixture():
    """创建带临时项目的 loop fixture"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "calculator.py"), "w") as f:
            f.write("""def add(a, b):
    return a + b

def divide(a, b):
    return a / b
""")
        code_model = MockCodeModelClient()
        sandbox = SandboxValidator(path, config=SandboxConfig(check_tests=False))
        applier = IncrementApplier(path)
        config = LoopConfig(max_iterations=3, enable_auto_apply=False)
        loop = ModificationLoop(code_model, sandbox, applier, config)
        yield loop, path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.asyncio
async def test_loop_success_on_first_try(loop_fixture):
    loop, path = loop_fixture
    result = await loop.run(
        task_description="Add docstring to add function",
        file_context={"calculator.py": open(os.path.join(path, "calculator.py")).read()},
    )
    assert result.success is True
    assert result.iterations == 1
    assert result.final_validation is not None
    assert result.final_validation.success is True


@pytest.mark.asyncio
async def test_loop_disabled_sandbox_skips_validation(loop_fixture):
    loop, path = loop_fixture
    from blueclaw.adapter.ide.models import SandboxConfig
    loop.sandbox.config = SandboxConfig(enabled=False)
    result = await loop.run(
        task_description="Add docstring",
        file_context={"calculator.py": open(os.path.join(path, "calculator.py")).read()},
    )
    assert result.success is True
    assert result.iterations == 1


@pytest.mark.asyncio
async def test_loop_max_iterations_exhausted(loop_fixture):
    loop, path = loop_fixture
    # 模拟总是失败的验证：注入一个 broken diff
    diff_text = """diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,3 @@
 def add(a, b):
+    broken syntax here (
     return a + b
"""
    loop.code_model = MockCodeModelClient(response_template=diff_text)
    result = await loop.run(
        task_description="Break the code",
        file_context={"calculator.py": open(os.path.join(path, "calculator.py")).read()},
    )
    assert result.success is False
    assert result.iterations == 3
    assert len(result.iteration_history) == 3
    assert result.paused_for_human is True


@pytest.mark.asyncio
async def test_loop_feedback_formatting(loop_fixture):
    loop, path = loop_fixture
    validation = SandboxValidationResult(
        success=False,
        checks=[
            ValidationCheck(check_type="syntax", passed=False, details="Syntax error on line 3", stderr="  File x.py, line 3\n    def foo(\n          ^\nSyntaxError"),
        ],
    )
    feedback = loop._build_feedback(validation)
    assert "SYNTAX FAILED" in feedback
    assert "Syntax error on line 3" in feedback
    assert "```" in feedback


@pytest.mark.asyncio
async def test_loop_debug_log_populated(loop_fixture):
    loop, path = loop_fixture
    result = await loop.run(
        task_description="Add docstring",
        file_context={"calculator.py": open(os.path.join(path, "calculator.py")).read()},
    )
    assert len(result.debug_log) > 0
    assert "[Loop] Starting modification loop" in result.debug_log[0]
    assert any("[Loop] === Iteration" in line for line in result.debug_log)


@pytest.mark.asyncio
async def test_loop_iteration_history(loop_fixture):
    loop, path = loop_fixture
    result = await loop.run(
        task_description="Add docstring",
        file_context={"calculator.py": open(os.path.join(path, "calculator.py")).read()},
    )
    assert len(result.iteration_history) == 1
    iter_record = result.iteration_history[0]
    assert iter_record.iteration == 1
    assert iter_record.code_model_response is not None
    assert iter_record.validation_result is not None
    assert iter_record.duration_ms > 0


@pytest.mark.asyncio
async def test_loop_with_auto_apply(loop_fixture):
    loop, path = loop_fixture
    # 初始化 git 仓库以便 auto_apply 工作
    import subprocess
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)

    loop.config.enable_auto_apply = True
    result = await loop.run(
        task_description="Add docstring",
        file_context={"calculator.py": open(os.path.join(path, "calculator.py")).read()},
    )
    assert result.success is True
    assert result.final_apply is not None
    # 文件已被修改
    with open(os.path.join(path, "calculator.py"), "r") as f:
        content = f.read()
    # mock 会追加注释行
    assert "Modified by CodeModel" in content


@pytest.mark.asyncio
async def test_loop_pause_on_failure_disabled(loop_fixture):
    loop, path = loop_fixture
    loop.config.pause_on_failure = False
    diff_text = """diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,3 @@
 def add(a, b):
+    broken (
     return a + b
"""
    loop.code_model = MockCodeModelClient(response_template=diff_text)
    result = await loop.run(
        task_description="Break code",
        file_context={"calculator.py": open(os.path.join(path, "calculator.py")).read()},
    )
    assert result.success is False
    assert result.paused_for_human is False
