# -*- coding: utf-8 -*-
"""
稳定性测试 - 资源释放

- 临时目录清理
- 沙盒销毁验证
- 检查点过期清理
"""
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.models import SandboxConfig
from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2


def test_sandbox_auto_destroyed():
    """沙盒验证后自动销毁"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "main.py"), "w") as f:
            f.write("def foo(): pass\n")

        validator = SandboxValidator(path, SandboxConfig(check_tests=False))
        import asyncio
        sandbox_path = validator._create_sandbox()
        assert os.path.exists(sandbox_path)
        validator._destroy_sandbox(sandbox_path)
        assert not os.path.exists(sandbox_path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_checkpoint_cleanup():
    """检查点管理器正确清理过期记录"""
    path = tempfile.mkdtemp()
    try:
        cm = CheckpointManagerV2(base_dir=path)
        from blueclaw.adapter.core.operation_record import OperationRecord, StepResult
        for i in range(10):
            cm.save_from_record(OperationRecord(
                record_id=f"rec_{i}",
                blueprint_id="test",
                step_id=f"step_{i}",
                step_type="wait",
                params={},
                result=StepResult(status="success"),
                timestamp=float(i),
            ))

        all_records = cm.list_checkpoints("test")
        assert len(all_records) == 10

        # 删除全部
        cm.delete_all("test")
        assert len(cm.list_checkpoints("test")) == 0
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_temp_file_cleanup_in_applier():
    """应用器不留下临时文件"""
    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "file.py"), "w") as f:
            f.write("pass\n")

        from blueclaw.adapter.ide.applier import IncrementApplier
        from blueclaw.adapter.ide.models import FileDiff, DiffHunk

        applier = IncrementApplier(path)
        diff = FileDiff(
            file_path="file.py",
            hunks=[DiffHunk(old_start=1, old_lines=1, new_start=1, new_lines=1, lines=["-pass", "+return"])],
        )
        result = applier.apply_diffs([diff], auto_commit=False)
        assert result.success is True

        # 不应有额外的临时文件
        files = os.listdir(path)
        assert "file.py" in files
        # 没有 .tmp 或备份文件
        assert not any(f.endswith(".tmp") or f.endswith(".bak") for f in files)
    finally:
        shutil.rmtree(path, ignore_errors=True)
