# -*- coding: utf-8 -*-
"""
SandboxValidator - 沙盒验证器

- 本地临时目录沙盒（无需 Docker）
- Docker 沙盒（生产环境）
- 编译/语法检查
- 静态分析（pylint/eslint）
- 单元测试执行（pytest/jest）
- 验证结果收集
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Optional, Any

from blueclaw.adapter.ide.models import (
    SandboxConfig, SandboxValidationResult, ValidationCheck,
    FileDiff, DiffHunk,
)


class SandboxValidator:
    """沙盒验证器"""

    def __init__(self, project_path: str, config: Optional[SandboxConfig] = None):
        self.project_path = os.path.abspath(project_path)
        self.config = config or SandboxConfig()

    async def validate(
        self,
        diffs: List[FileDiff],
    ) -> SandboxValidationResult:
        """在沙盒中验证代码修改"""
        if not self.config.enabled:
            return SandboxValidationResult(
                success=True, summary="Sandbox validation disabled"
            )

        start_time = time.time()
        checks: List[ValidationCheck] = []
        sandbox_path: Optional[str] = None

        try:
            # 1. 创建沙盒
            sandbox_path = self._create_sandbox()

            # 2. 应用修改到沙盒
            self._apply_diffs(sandbox_path, diffs)

            # 3. 语法检查
            if self.config.check_syntax:
                checks.append(self._check_syntax(sandbox_path))

            # 4. 静态分析
            if self.config.check_static_analysis:
                checks.append(self._check_static_analysis(sandbox_path))

            # 5. 单元测试
            if self.config.check_tests:
                checks.append(self._run_tests(sandbox_path))

        except Exception as e:
            return SandboxValidationResult(
                success=False,
                checks=checks,
                summary=f"Sandbox validation failed: {e}",
                total_duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
        finally:
            if sandbox_path:
                self._destroy_sandbox(sandbox_path)

        total_duration = (time.time() - start_time) * 1000
        all_passed = all(c.passed for c in checks)

        return SandboxValidationResult(
            success=all_passed,
            checks=checks,
            summary=self._build_summary(checks),
            total_duration_ms=total_duration,
        )

    def _create_sandbox(self) -> str:
        """创建沙盒环境"""
        if self.config.use_docker:
            return self._create_docker_sandbox()
        return self._create_local_sandbox()

    def _create_local_sandbox(self) -> str:
        """创建本地临时目录沙盒"""
        sandbox = tempfile.mkdtemp(prefix="blueclaw_sandbox_")
        # 复制项目代码到沙盒
        for root, dirs, files in os.walk(self.project_path):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if d not in {
                "__pycache__", ".git", ".venv", "venv",
                "node_modules", ".pytest_cache", "dist", "build",
            }]
            rel_root = os.path.relpath(root, self.project_path)
            dest_root = os.path.join(sandbox, rel_root)
            os.makedirs(dest_root, exist_ok=True)
            for fname in files:
                src = os.path.join(root, fname)
                dst = os.path.join(dest_root, fname)
                shutil.copy2(src, dst)
        return sandbox

    def _create_docker_sandbox(self) -> str:
        """创建 Docker 沙盒（占位，需 Docker 环境）"""
        # TODO: 实现 Docker 容器启动和 Volume 挂载
        raise NotImplementedError("Docker sandbox not yet implemented")

    def _destroy_sandbox(self, sandbox_path: str) -> None:
        """销毁沙盒"""
        shutil.rmtree(sandbox_path, ignore_errors=True)

    def _apply_diffs(self, sandbox_path: str, diffs: List[FileDiff]) -> None:
        """将 diff 应用到沙盒代码"""
        for diff in diffs:
            file_path = os.path.join(sandbox_path, diff.file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 读取原始内容
            original_lines: List[str] = []
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    original_lines = f.read().splitlines()

            # 应用 hunk
            new_lines = self._apply_hunks(original_lines, diff.hunks)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
                if new_lines:
                    f.write("\n")

    def _apply_hunks(self, original_lines: List[str], hunks: List[DiffHunk]) -> List[str]:
        """应用 diff hunks 到文件内容（简化版）"""
        result = list(original_lines)
        # 从后向前应用，避免行号偏移
        for hunk in reversed(hunks):
            old_start = max(0, hunk.old_start - 1)
            new_lines_hunk: List[str] = []
            for line in hunk.lines:
                if line.startswith("+") and not line.startswith("+++"):
                    new_lines_hunk.append(line[1:])
                elif line.startswith("-") and not line.startswith("---"):
                    continue
                elif line.startswith(" "):
                    new_lines_hunk.append(line[1:])
                elif line.startswith("\\"):
                    continue  # \ No newline at end of file
                else:
                    new_lines_hunk.append(line)
            result = result[:old_start] + new_lines_hunk + result[old_start + hunk.old_lines:]
        return result

    def _check_syntax(self, sandbox_path: str) -> ValidationCheck:
        """语法检查（Python）"""
        start = time.time()
        errors: List[str] = []
        checked = 0

        for root, _, files in os.walk(sandbox_path):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                checked += 1
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, sandbox_path)
                try:
                    with open(fpath, "rb") as f:
                        compile(f.read(), rel, "exec")
                except SyntaxError as e:
                    errors.append(f"{rel}:{e.lineno}: {e.msg}")
                except Exception as e:
                    errors.append(f"{rel}: {e}")

        duration = (time.time() - start) * 1000
        passed = len(errors) == 0

        return ValidationCheck(
            check_type="syntax",
            passed=passed,
            details=f"Checked {checked} Python files, {len(errors)} errors" if checked > 0 else "No Python files to check",
            duration_ms=duration,
            stderr="\n".join(errors),
        )

    def _check_static_analysis(self, sandbox_path: str) -> ValidationCheck:
        """静态分析（pylint，如果可用）"""
        start = time.time()
        pylint_path = shutil.which("pylint")
        if not pylint_path:
            return ValidationCheck(
                check_type="static_analysis",
                passed=True,
                details="pylint not installed, skipped",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            proc = subprocess.run(
                [pylint_path, "--errors-only", "--output-format=text", sandbox_path],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                cwd=sandbox_path,
            )
            duration = (time.time() - start) * 1000
            errors = [l for l in proc.stdout.splitlines() if l.strip() and "error" in l.lower()]
            passed = len(errors) == 0 and proc.returncode == 0
            return ValidationCheck(
                check_type="static_analysis",
                passed=passed,
                details=f"pylint: {len(errors)} errors" if errors else "pylint: clean",
                duration_ms=duration,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except Exception as e:
            return ValidationCheck(
                check_type="static_analysis",
                passed=False,
                details=f"Static analysis failed: {e}",
                duration_ms=(time.time() - start) * 1000,
                stderr=str(e),
            )

    def _run_tests(self, sandbox_path: str) -> ValidationCheck:
        """运行单元测试（pytest，如果可用）"""
        start = time.time()
        pytest_path = shutil.which("pytest")
        if not pytest_path:
            return ValidationCheck(
                check_type="test",
                passed=True,
                details="pytest not installed, skipped",
                duration_ms=(time.time() - start) * 1000,
            )

        # 查找测试目录
        test_dirs = [d for d in os.listdir(sandbox_path)
                     if os.path.isdir(os.path.join(sandbox_path, d)) and "test" in d.lower()]
        if not test_dirs:
            # 尝试根目录
            test_dirs = ["."]

        try:
            proc = subprocess.run(
                [pytest_path, "-q", "--tb=short"] + test_dirs,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                cwd=sandbox_path,
            )
            duration = (time.time() - start) * 1000
            passed = proc.returncode == 0
            stdout = proc.stdout
            # 解析测试统计
            summary_line = ""
            for line in stdout.splitlines():
                if "passed" in line or "failed" in line:
                    summary_line = line.strip()
                    break
            return ValidationCheck(
                check_type="test",
                passed=passed,
                details=summary_line or f"pytest exit code: {proc.returncode}",
                duration_ms=duration,
                stdout=stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            return ValidationCheck(
                check_type="test",
                passed=False,
                details="Tests timed out",
                duration_ms=(time.time() - start) * 1000,
                stderr="Timeout",
            )
        except Exception as e:
            return ValidationCheck(
                check_type="test",
                passed=False,
                details=f"Test execution failed: {e}",
                duration_ms=(time.time() - start) * 1000,
                stderr=str(e),
            )

    def _build_summary(self, checks: List[ValidationCheck]) -> str:
        """构建验证摘要"""
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        failed = [c.check_type for c in checks if not c.passed]
        if failed:
            return f"Validation: {passed}/{total} passed. Failed: {', '.join(failed)}"
        return f"Validation: {passed}/{total} passed. All clear."
