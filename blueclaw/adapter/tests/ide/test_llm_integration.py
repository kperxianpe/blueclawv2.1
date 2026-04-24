# -*- coding: utf-8 -*-
"""
LLM Integration Test - 使用真实 Kimi API 测试 IDE Pipeline

运行前确保 .env 文件包含 KIMI_API_KEY

环境变量方式:
  KIMI_API_KEY=xxx pytest tests/ide/test_llm_integration.py -v

或自动读取上级目录 .env:
  pytest tests/ide/test_llm_integration.py -v
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
from blueclaw.adapter.ide.planner import ArchitecturePlanner
from blueclaw.adapter.ide.codemodel import KimiCodeClient
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.loop import ModificationLoop
from blueclaw.adapter.ide.models import (
    SandboxConfig, LoopConfig,
)
from blueclaw.adapter.models import (
    ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription,
)


def _load_env():
    """尝试从 .env 文件加载环境变量"""
    env_paths = [
        Path(".env"),
        Path(__file__).resolve().parents[4] / ".env",  # 项目根目录
        Path(__file__).resolve().parents[5] / ".env",  # 上级目录
    ]
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
            return


_load_env()

KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
HAS_KIMI_KEY = bool(KIMI_API_KEY and KIMI_API_KEY.startswith("sk-"))


@pytest.fixture
def buggy_project():
    """创建一个有除零 bug 的临时 Python 项目（带 Git）"""
    path = tempfile.mkdtemp(prefix="blueclaw_llm_test_")
    try:
        # 初始化 git
        subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@blueclaw.ai"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)

        with open(os.path.join(path, "calculator.py"), "w") as f:
            f.write('"""Calculator module."""\n\n\ndef divide(a, b):\n    """Divide a by b."""\n    return a / b\n\ndef multiply(a, b):\n    """Multiply a and b."""\n    return a * b\n')

        with open(os.path.join(path, "test_calculator.py"), "w") as f:
            f.write('import pytest\nfrom calculator import divide, multiply\n\ndef test_divide_normal():\n    assert divide(10, 2) == 5\n\ndef test_divide_by_zero():\n    with pytest.raises(ValueError):\n        divide(10, 0)\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n')

        subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)

        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.skipif(not HAS_KIMI_KEY, reason="KIMI_API_KEY not configured")
@pytest.mark.asyncio
async def test_llm_pipeline_divide_by_zero(buggy_project):
    """端到端测试：使用真实 Kimi API 修复除零错误"""
    project = buggy_project
    print(f"\n[LLM Test] Project: {project}")

    # Step 1: 代码分析
    analyzer = CodebaseAnalyzer(project)
    analysis = analyzer.analyze()
    assert analysis.total_files >= 2
    print(f"[LLM Test] Analyzed {analysis.total_files} files")

    # Step 2: 架构规划
    planner = ArchitecturePlanner()
    blueprint = ExecutionBlueprint(
        task_id="llm_test_fix_divzero",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="fix_divide",
                name="Fix divide by zero in calculator.py",
                action=ActionDefinition(
                    type="edit_file",
                    target=TargetDescription(semantic="calculator.py"),
                    params={"estimated_lines": 5},
                ),
            ),
        ],
    )
    plan = planner.plan(blueprint, analysis)
    assert len(plan.tasks) >= 1
    print(f"[LLM Test] Planned {len(plan.tasks)} tasks")

    # Step 3: 调用真实 Kimi API
    file_context = {
        "calculator.py": open(os.path.join(project, "calculator.py")).read(),
    }
    code_model = KimiCodeClient(
        api_key=KIMI_API_KEY,
        base_url=os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        model=os.environ.get("KIMI_MODEL", "moonshot-v1-8k"),
    )

    response = await code_model.generate_code_changes(
        task_description="Fix the divide function to handle division by zero. Raise ValueError with a clear message when b is 0.",
        file_context=file_context,
        constraints=[
            "Only modify the divide function",
            "Keep the existing docstring",
            "Use unified diff format",
        ],
    )

    print(f"[LLM Test] Code model response: success={response.success}, diffs={len(response.diffs)}, tokens={response.tokens_used}")
    if not response.success:
        pytest.fail(f"Kimi API failed: {response.error}")

    assert len(response.diffs) > 0, "Expected at least one diff from LLM"
    print(f"[LLM Test] Diff files: {[d.file_path for d in response.diffs]}")

    # Step 4: 沙盒验证
    sandbox = SandboxValidator(
        project,
        config=SandboxConfig(check_syntax=True, check_tests=True, check_static_analysis=False),
    )
    validation = await sandbox.validate(response.diffs)

    print(f"[LLM Test] Validation: {validation.summary}")
    for check in validation.checks:
        print(f"[LLM Test]   - {check.check_type}: {'PASS' if check.passed else 'FAIL'} - {check.details}")

    # 即使验证失败也继续，用于观察 LLM 输出质量
    if not validation.success:
        print(f"[LLM Test] WARNING: Validation failed (this is OK for observing LLM quality)")
        # 打印失败详情用于调试
        for check in validation.failed_checks:
            print(f"[LLM Test]   FAIL detail: {check.details}")
            if check.stderr:
                print(f"[LLM Test]   stderr: {check.stderr[:500]}")

    # Step 5: 应用到主库（即使验证失败也应用，方便人工检查）
    applier = IncrementApplier(project)
    apply_result = applier.apply_diffs(response.diffs, auto_commit=False)

    print(f"[LLM Test] Apply result: success={apply_result.success}, files={apply_result.files_changed}")
    assert apply_result.success, f"Apply failed: {apply_result.error}"

    # Step 6: 验证文件内容
    with open(os.path.join(project, "calculator.py"), "r") as f:
        final_content = f.read()

    print(f"[LLM Test] Final calculator.py:\n{final_content}")

    # 检查是否包含修复
    has_fix = "zero" in final_content.lower() or "ValueError" in final_content or "raise" in final_content
    print(f"[LLM Test] Detected fix indicator: {has_fix}")

    # 运行测试
    proc = subprocess.run(
        ["python", "-m", "pytest", "-q", os.path.join(project, "test_calculator.py")],
        cwd=project,
        capture_output=True,
        text=True,
    )
    tests_passed = proc.returncode == 0
    print(f"[LLM Test] Tests: {proc.stdout.strip()[-200:] if proc.stdout else 'N/A'}")
    print(f"[LLM Test] Tests passed: {tests_passed}")

    # 断言：LLM 至少生成了有效的 diff
    assert len(response.diffs) > 0
    assert response.tokens_used > 0
    assert apply_result.success

    # 软性断言：如果测试通过则更好，但不强制
    if tests_passed:
        print("[LLM Test] [PASS] All tests passed - LLM generated correct fix!")
    else:
        print("[LLM Test] [WARN] Tests failed - LLM output may need refinement")


@pytest.mark.skipif(not HAS_KIMI_KEY, reason="KIMI_API_KEY not configured")
@pytest.mark.asyncio
async def test_llm_loop_with_retry(buggy_project):
    """测试循环控制器：LLM -> Sandbox -> (retry if needed)"""
    project = buggy_project

    code_model = KimiCodeClient(
        api_key=KIMI_API_KEY,
        base_url=os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        model=os.environ.get("KIMI_MODEL", "moonshot-v1-8k"),
    )
    sandbox = SandboxValidator(
        project,
        config=SandboxConfig(check_syntax=True, check_tests=True, check_static_analysis=False),
    )
    applier = IncrementApplier(project)
    loop = ModificationLoop(
        code_model=code_model,
        sandbox=sandbox,
        applier=applier,
        config=LoopConfig(max_iterations=2, enable_auto_apply=False),
    )

    file_context = {
        "calculator.py": open(os.path.join(project, "calculator.py")).read(),
    }

    result = await loop.run(
        task_description="Fix the divide function to handle division by zero. Raise ValueError when b is 0.",
        file_context=file_context,
        constraints=["Only modify the divide function", "Keep docstring"],
    )

    print(f"\n[LLM Loop Test] Success: {result.success}")
    print(f"[LLM Loop Test] Iterations: {result.iterations}")
    print(f"[LLM Loop Test] Paused for human: {result.paused_for_human}")
    print(f"[LLM Loop Test] Debug log ({len(result.debug_log)} lines):")
    for line in result.debug_log:
        print(f"  {line}")

    # 基本断言
    assert result.iterations >= 1
    assert len(result.iteration_history) > 0
    assert result.iteration_history[0].code_model_response is not None
    assert result.iteration_history[0].code_model_response.tokens_used > 0

    # 如果成功则验证应用到文件
    if result.success and result.final_apply:
        print(f"[LLM Loop Test] Applied commit: {result.final_apply.commit_hash[:8] if result.final_apply.commit_hash else 'N/A'}")
