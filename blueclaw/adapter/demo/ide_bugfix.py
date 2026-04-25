# -*- coding: utf-8 -*-
"""
Demo: IDE Bug Fix 完整流程

演示 Week 27 的完整修改-验证-应用循环：
1. 代码分析
2. 架构规划
3. 调用代码模型
4. 沙盒验证
5. 循环重试（模拟）
6. 应用到主库

运行: python -m blueclaw.adapter.demo.ide_bugfix
"""
import asyncio
import os
import shutil
import subprocess
import tempfile


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_step(step, status="..."):
    icon = "OK" if status == "pass" else "FAIL" if status == "fail" else ".."
    print(f"  [{icon}] {step}")


async def main():
    print_section("BlueClaw IDE Adapter - Bug Fix Demo")
    print("\n[任务] 修复 calculator.py 的除零错误\n")

    # 创建临时项目
    project = tempfile.mkdtemp(prefix="blueclaw_demo_")
    try:
        # 初始化 git
        subprocess.run(["git", "init"], cwd=project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "demo@blueclaw.ai"], cwd=project, capture_output=True)
        subprocess.run(["git", "config", "user.name", "BlueClaw Demo"], cwd=project, capture_output=True)

        # 创建有 bug 的代码
        calc_path = os.path.join(project, "calculator.py")
        with open(calc_path, "w") as f:
            f.write('"""Simple calculator module."""\n\n\ndef divide(a, b):\n    """Divide a by b."""\n    return a / b\n')

        test_path = os.path.join(project, "test_calculator.py")
        with open(test_path, "w") as f:
            f.write('import pytest\nfrom calculator import divide\n\ndef test_divide_normal():\n    assert divide(10, 2) == 5\n\ndef test_divide_by_zero():\n    with pytest.raises(ValueError):\n        divide(10, 0)\n')

        subprocess.run(["git", "add", "."], cwd=project, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init: add calculator with bug"], cwd=project, capture_output=True)

        print(f"  Project: {project}")
        print(f"  Files: calculator.py, test_calculator.py")

        # Step 1: 代码分析
        print_section("Step 1: Codebase Analysis")
        from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer(project)
        analysis = analyzer.analyze()
        print_step(f"Scanned {analysis.total_files} files, {analysis.total_lines} lines", "pass")
        print_step(f"Languages: {analysis.languages}", "pass")
        print_step(f"Symbols: {sum(len(f.symbols) for f in analysis.files)}", "pass")

        # Step 2: 架构规划
        print_section("Step 2: Architecture Planning")
        from blueclaw.adapter.ide.planner import ArchitecturePlanner
        from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription

        planner = ArchitecturePlanner()
        blueprint = ExecutionBlueprint(
            task_id="demo_fix_divzero",
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
        print_step(f"Generated {len(plan.tasks)} tasks", "pass")
        print_step(f"Affected files: {plan.affected_files}", "pass")
        print_step(f"Execution order: {plan.execution_order}", "pass")

        # Step 3: 调用代码模型
        print_section("Step 3: Code Model (Kimi Code)")
        from blueclaw.adapter.ide.codemodel import MockCodeModelClient

        # 使用模板生成正确的修复
        fix_diff = '''diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -3,4 +3,6 @@
 
 def divide(a, b):
     """Divide a by b."""
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
     return a / b
'''
        code_model = MockCodeModelClient(response_template=fix_diff)
        response = await code_model.generate_code_changes(
            task_description="Fix divide by zero error",
            file_context={"calculator.py": open(calc_path).read()},
        )
        print_step(f"Model returned {len(response.diffs)} diffs", "pass")
        for diff in response.diffs:
            print_step(f"  -> {diff.file_path} (+{diff.additions}/-{diff.deletions})", "pass")

        # Step 4: 沙盒验证
        print_section("Step 4: Sandbox Validation")
        from blueclaw.adapter.ide.sandbox import SandboxValidator
        from blueclaw.adapter.ide.models import SandboxConfig

        sandbox = SandboxValidator(
            project,
            config=SandboxConfig(check_syntax=True, check_tests=True, check_static_analysis=False),
        )
        validation = await sandbox.validate(response.diffs)
        for check in validation.checks:
            status = "pass" if check.passed else "fail"
            print_step(f"{check.check_type}: {check.details}", status)
        print_step(f"Summary: {validation.summary}", "pass" if validation.success else "fail")
        print_step(f"Duration: {validation.total_duration_ms:.0f}ms", "pass")

        if not validation.success:
            print("\n  [Demo] Validation failed - showing retry logic...")
            # 模拟重试反馈
            from blueclaw.adapter.ide.loop import ModificationLoop
            loop = ModificationLoop(
                code_model=code_model,
                sandbox=sandbox,
                config=LoopConfig(max_iterations=1),
            )
            result = await loop.run(
                task_description="Fix divide by zero",
                file_context={"calculator.py": open(calc_path).read()},
            )
            if not result.success:
                print_step("Retry would happen here in full loop", "pass")

        # Step 5: 应用到主库
        print_section("Step 5: Apply to Main Repository")
        from blueclaw.adapter.ide.applier import IncrementApplier

        applier = IncrementApplier(project)
        apply_result = applier.apply_diffs(
            response.diffs,
            auto_commit=True,
            commit_message='''fix(calculator): handle division by zero

- Add check for zero divisor
- Raise ValueError with clear message
- Fixes test_divide_by_zero

Modified by BlueClaw IDE Adapter''',
        )
        if apply_result.success:
            print_step("Diff applied to files", "pass")
            print_step(f"Files changed: {apply_result.files_changed}", "pass")
            if apply_result.committed:
                print_step(f"Git commit: {apply_result.commit_hash[:8]}", "pass")
                print_step(f"Commit message preview: {apply_result.commit_message.split(chr(10))[0]}", "pass")

        # Step 6: 验证最终状态
        print_section("Step 6: Final Verification")
        with open(calc_path, "r") as f:
            content = f.read()
        assert "Cannot divide by zero" in content
        print_step("Source code contains fix", "pass")

        # 运行测试
        proc = subprocess.run(
            ["python", "-m", "pytest", "-q", test_path],
            cwd=project,
            capture_output=True,
            text=True,
        )
        tests_passed = proc.returncode == 0
        print_step(f"Tests: {proc.stdout.strip().splitlines()[-1] if proc.stdout else 'N/A'}",
                   "pass" if tests_passed else "fail")

        # Git log
        log_proc = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            cwd=project,
            capture_output=True,
            text=True,
        )
        print_step("Git history:", "pass")
        for line in log_proc.stdout.strip().splitlines():
            print(f"      {line}")

        print_section("Demo Complete")
        print(f"\n  Project path: {project}")
        print(f"  All tests passed: {tests_passed}")
        print(f"  Commit created: {apply_result.commit_hash[:8] if apply_result.commit_hash else 'N/A'}")

    finally:
        # 清理（可选：取消注释以保留）
        shutil.rmtree(project, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
