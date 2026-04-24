# -*- coding: utf-8 -*-
"""
CheckpointManagerV2 - 基于 OperationRecord 的检查点管理

- save_from_record
- restore
- list_checkpoints
- cleanup (保留最近 N 个)
"""
import os
import json
import shutil
from typing import Dict, List, Optional

from blueclaw.adapter.core.operation_record import OperationRecord, OperationLog


class CheckpointManagerV2:
    """增强型检查点管理器"""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "sessions", "checkpoints"
            )
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _dir(self, blueprint_id: str) -> str:
        return os.path.join(self.base_dir, blueprint_id)

    def _path(self, blueprint_id: str, record_id: str) -> str:
        return os.path.join(self._dir(blueprint_id), f"{record_id}.json")

    def save_from_record(self, record: OperationRecord) -> str:
        """从 OperationRecord 保存检查点"""
        d = self._dir(record.blueprint_id)
        os.makedirs(d, exist_ok=True)
        path = self._path(record.blueprint_id, record.record_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    def restore(self, blueprint_id: str, record_id: str) -> Optional[OperationRecord]:
        """从检查点恢复 OperationRecord"""
        path = self._path(blueprint_id, record_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return OperationRecord.from_dict(json.load(f))

    def list_checkpoints(self, blueprint_id: str) -> List[Dict]:
        """列出某蓝图的所有检查点（按文件修改时间排序）"""
        d = self._dir(blueprint_id)
        if not os.path.exists(d):
            return []
        files = []
        for fname in os.listdir(d):
            if fname.endswith(".json"):
                path = os.path.join(d, fname)
                files.append({
                    "record_id": fname[:-5],
                    "path": path,
                    "mtime": os.path.getmtime(path),
                })
        files.sort(key=lambda x: x["mtime"])
        return files

    def cleanup(self, blueprint_id: str, keep_last_n: int = 10) -> int:
        """清理旧检查点，只保留最近 N 个"""
        checkpoints = self.list_checkpoints(blueprint_id)
        if len(checkpoints) <= keep_last_n:
            return 0
        removed = 0
        for cp in checkpoints[:-keep_last_n]:
            try:
                os.remove(cp["path"])
                removed += 1
            except Exception:
                pass
        return removed

    def delete_all(self, blueprint_id: str) -> None:
        """删除某蓝图的所有检查点"""
        d = self._dir(blueprint_id)
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
