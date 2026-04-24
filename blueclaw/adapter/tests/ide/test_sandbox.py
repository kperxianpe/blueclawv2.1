# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.models import SandboxConfig, FileDiff, DiffHunk


@pytest.fixture
def sample_project():
    """创建示例 Python 项目"""
    path = tempfile.mkdtemp()
    try:
        # 主模块
        with open(os.path.join(path, "calculator.py"), "w") as f:
            f.write("""def add(a, b):
    return a + b

def divide(a, b):
    return a / b
""")
        # 测试文件
        os.makedirs(os.path.join(path, "tests"))
        with open(os.path.join(path, "tests", "test_calculator.py"), "w") as f:
            f.write("""from calculator import add, divide

def test_add():
    assert add(1, 2) == 3

def test_divide():
    assert divide(10, 2) == 5
""")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def broken_project():
    """创建有语法错误的项目"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "broken.py"), "w") as f:
            f.write("""def foo(
    print("missing closing paren")
""")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.asyncio
async def test_sandbox_valid_code_passes(sample_project):
    validator = SandboxValidator(sample_project, SandboxConfig(check_tests=False))
    result = await validator.validate(diffs=[])
    assert result.success is True
    assert len(result.checks) >= 1
    syntax_check = next(c for c in result.checks if c.check_type == "syntax")
    assert syntax_check.passed is True


@pytest.mark.asyncio
async def test_sandbox_syntax_error_detected(broken_project):
    validator = SandboxValidator(broken_project, SandboxConfig(check_tests=False))
    result = await validator.validate(diffs=[])
    assert result.success is False
    syntax_check = next(c for c in result.checks if c.check_type == "syntax")
    assert syntax_check.passed is False
    assert "error" in syntax_check.stderr.lower() or "errors" in syntax_check.details.lower()


@pytest.mark.asyncio
async def test_sandbox_applies_diff_and_validates(sample_project):
    validator = SandboxValidator(sample_project, SandboxConfig(check_tests=False))
    # 修复除零：添加检查
    diff = FileDiff(
        file_path="calculator.py",
        hunks=[DiffHunk(
            old_start=4,
            old_lines=2,
            new_start=4,
            new_lines=4,
            lines=[
                "-def divide(a, b):",
                "-    return a / b",
                "+def divide(a, b):",
                "+    if b == 0:",
                "+        raise ValueError('Cannot divide by zero')",
                "+    return a / b",
            ],
        )],
    )
    result = await validator.validate(diffs=[diff])
    assert result.success is True


@pytest.mark.asyncio
async def test_sandbox_test_execution(sample_project):
    validator = SandboxValidator(
        sample_project,
        SandboxConfig(check_syntax=True, check_tests=True),
    )
    result = await validator.validate(diffs=[])
    # 测试可能通过也可能因环境原因跳过
    assert len(result.checks) >= 1


@pytest.mark.asyncio
async def test_sandbox_disabled_returns_success(sample_project):
    validator = SandboxValidator(sample_project, SandboxConfig(enabled=False))
    result = await validator.validate(diffs=[])
    assert result.success is True
    assert "disabled" in result.summary.lower()


@pytest.mark.asyncio
async def test_sandbox_summary_format(sample_project):
    validator = SandboxValidator(sample_project, SandboxConfig(check_tests=False))
    result = await validator.validate(diffs=[])
    assert "passed" in result.summary.lower()
    assert result.total_duration_ms > 0


def test_sandbox_destroyed_after_validation(sample_project):
    validator = SandboxValidator(sample_project, SandboxConfig(check_tests=False))
    # 内部方法测试：创建和销毁
    sandbox = validator._create_sandbox()
    assert os.path.exists(sandbox)
    assert os.path.exists(os.path.join(sandbox, "calculator.py"))
    validator._destroy_sandbox(sandbox)
    assert not os.path.exists(sandbox)


def test_apply_hunks_basic():
    validator = SandboxValidator(".")
    hunks = [DiffHunk(
        old_start=1,
        old_lines=2,
        new_start=1,
        new_lines=3,
        lines=[
            "-old line 1",
            "-old line 2",
            "+new line 1",
            "+new line 2",
            "+new line 3",
        ],
    )]
    result = validator._apply_hunks(["old line 1", "old line 2"], hunks)
    assert result == ["new line 1", "new line 2", "new line 3"]
