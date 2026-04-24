# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import subprocess
import pytest

from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.models import FileDiff, DiffHunk


@pytest.fixture
def temp_project():
    """创建临时项目目录（无 Git）"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "main.py"), "w") as f:
            f.write("def main():\n    pass\n")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def git_project():
    """创建带 Git 仓库的临时项目"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "main.py"), "w") as f:
            f.write("def main():\n    pass\n")
        subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_apply_diff_without_git(temp_project):
    applier = IncrementApplier(temp_project)
    diff = FileDiff(
        file_path="main.py",
        hunks=[DiffHunk(
            old_start=1,
            old_lines=2,
            new_start=1,
            new_lines=3,
            lines=[
                "-def main():",
                "-    pass",
                "+def main():",
                "+    print('hello')",
                "+    return 0",
            ],
        )],
    )
    result = applier.apply_diffs([diff], auto_commit=False)
    assert result.success is True
    assert "main.py" in result.files_changed
    # 检查文件内容
    with open(os.path.join(temp_project, "main.py"), "r") as f:
        content = f.read()
    assert "print('hello')" in content
    assert "return 0" in content


def test_git_status_clean(git_project):
    applier = IncrementApplier(git_project)
    status = applier.get_git_status()
    assert status.is_clean is True
    assert status.has_conflicts is False


def test_git_status_after_modify(git_project):
    applier = IncrementApplier(git_project)
    diff = FileDiff(
        file_path="main.py",
        hunks=[DiffHunk(
            old_start=1,
            old_lines=2,
            new_start=1,
            new_lines=3,
            lines=[
                "-def main():",
                "-    pass",
                "+def main():",
                "+    print('hello')",
                "+    return 0",
            ],
        )],
    )
    applier.apply_diffs([diff], auto_commit=False)
    status = applier.get_git_status()
    assert status.is_clean is False
    assert "main.py" in status.modified_files


def test_apply_with_auto_commit(git_project):
    applier = IncrementApplier(git_project)
    diff = FileDiff(
        file_path="main.py",
        hunks=[DiffHunk(
            old_start=1,
            old_lines=2,
            new_start=1,
            new_lines=3,
            lines=[
                "-def main():",
                "-    pass",
                "+def main():",
                "+    print('hello')",
                "+    return 0",
            ],
        )],
    )
    result = applier.apply_diffs([diff], auto_commit=True)
    assert result.success is True
    assert result.committed is True
    assert result.commit_hash != ""
    assert "main.py" in result.files_changed
    assert result.rollback_available is True


def test_commit_message_generation(git_project):
    applier = IncrementApplier(git_project)
    diff = FileDiff(
        file_path="calculator.py",
        hunks=[DiffHunk(
            old_start=1,
            old_lines=1,
            new_start=1,
            new_lines=2,
            lines=[
                "-def add(a, b):",
                "+def add(a, b):",
                "+    # Fixed",
            ],
        )],
        additions=1,
        deletions=1,
    )
    result = applier.apply_diffs([diff], auto_commit=True)
    assert result.success is True
    assert "calculator" in result.commit_message.lower()
    assert "automated code modification" in result.commit_message.lower()


def test_rollback(git_project):
    applier = IncrementApplier(git_project)
    diff = FileDiff(
        file_path="main.py",
        hunks=[DiffHunk(
            old_start=1,
            old_lines=2,
            new_start=1,
            new_lines=3,
            lines=[
                "-def main():",
                "-    pass",
                "+def main():",
                "+    print('hello')",
                "+    return 0",
            ],
        )],
    )
    apply_result = applier.apply_diffs([diff], auto_commit=True)
    assert apply_result.success is True
    assert apply_result.pre_apply_head != ""

    # 回滚
    rollback_result = applier.rollback(apply_result.pre_apply_head)
    assert rollback_result.success is True

    # 验证文件恢复
    with open(os.path.join(git_project, "main.py"), "r") as f:
        content = f.read()
    assert "pass" in content
    assert "print" not in content


def test_revert_last_commit(git_project):
    applier = IncrementApplier(git_project)
    diff = FileDiff(
        file_path="main.py",
        hunks=[DiffHunk(
            old_start=1,
            old_lines=2,
            new_start=1,
            new_lines=3,
            lines=[
                "-def main():",
                "-    pass",
                "+def main():",
                "+    print('hello')",
                "+    return 0",
            ],
        )],
    )
    applier.apply_diffs([diff], auto_commit=True)

    revert_result = applier.revert_last_commit()
    assert revert_result.success is True
    assert revert_result.committed is True


def test_apply_creates_new_file(temp_project):
    applier = IncrementApplier(temp_project)
    diff = FileDiff(
        file_path="new_module.py",
        hunks=[DiffHunk(
            old_start=0,
            old_lines=0,
            new_start=1,
            new_lines=2,
            lines=[
                "+def helper():",
                "+    return 42",
            ],
        )],
    )
    result = applier.apply_diffs([diff], auto_commit=False)
    assert result.success is True
    assert "new_module.py" in result.files_changed
    assert os.path.exists(os.path.join(temp_project, "new_module.py"))
