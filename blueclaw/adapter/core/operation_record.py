# -*- coding: utf-8 -*-
"""
OperationRecord 操作记录系统

- 定义每个执行步骤的完整记录
- OperationLog 管理器（追加、查询、重新规划上下文、JSONL 持久化）
"""
import os
import json
import base64
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

from blueclaw.adapter.models import StepResult
from blueclaw.adapter.ui.intervention.base import InterventionResult


@dataclass
class OperationRecord:
    """每个执行步骤的完整记录"""
    record_id: str
    blueprint_id: str
    step_id: str
    step_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    result: StepResult = field(default_factory=lambda: StepResult(status="success"))
    before_screenshot: Optional[bytes] = None
    after_screenshot: Optional[bytes] = None
    timestamp: float = field(default_factory=time.time)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    has_intervention: bool = False
    intervention_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """序列化，截图用 base64"""
        return {
            "record_id": self.record_id,
            "blueprint_id": self.blueprint_id,
            "step_id": self.step_id,
            "step_type": self.step_type,
            "params": self.params,
            "result": self.result.model_dump(),
            "before_screenshot": base64.b64encode(self.before_screenshot).decode("utf-8") if self.before_screenshot else None,
            "after_screenshot": base64.b64encode(self.after_screenshot).decode("utf-8") if self.after_screenshot else None,
            "timestamp": self.timestamp,
            "state_snapshot": self.state_snapshot,
            "has_intervention": self.has_intervention,
            "intervention_type": self.intervention_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationRecord":
        return cls(
            record_id=data["record_id"],
            blueprint_id=data["blueprint_id"],
            step_id=data["step_id"],
            step_type=data["step_type"],
            params=data.get("params", {}),
            result=StepResult.model_validate(data.get("result", {"status": "success"})),
            before_screenshot=base64.b64decode(data["before_screenshot"]) if data.get("before_screenshot") else None,
            after_screenshot=base64.b64decode(data["after_screenshot"]) if data.get("after_screenshot") else None,
            timestamp=data.get("timestamp", time.time()),
            state_snapshot=data.get("state_snapshot", {}),
            has_intervention=data.get("has_intervention", False),
            intervention_type=data.get("intervention_type"),
        )


class OperationLog:
    """操作日志管理器"""

    def __init__(self, blueprint_id: str, base_dir: Optional[str] = None):
        self.blueprint_id = blueprint_id
        self._records: List[OperationRecord] = []
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "sessions", "operation_logs"
            )
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    @property
    def records(self) -> List[OperationRecord]:
        return list(self._records)

    def append(self, record: OperationRecord) -> None:
        self._records.append(record)

    def get_last_checkpoint(self) -> Optional[OperationRecord]:
        if not self._records:
            return None
        return self._records[-1]

    def get_records_since(self, record_id: str) -> List[OperationRecord]:
        found = False
        result = []
        for r in self._records:
            if found:
                result.append(r)
            if r.record_id == record_id:
                found = True
        return result

    def build_replan_context(
        self,
        record: OperationRecord,
        intervention: InterventionResult,
    ) -> Dict[str, Any]:
        return {
            "blueprint_id": record.blueprint_id,
            "checkpoint_record_id": record.record_id,
            "step_id": record.step_id,
            "state_snapshot": record.state_snapshot,
            "intervention": {
                "type": intervention.type,
                "text": intervention.text,
                "annotation": intervention.annotation,
                "choice": intervention.choice,
                "param_changes": intervention.param_changes,
            },
            "timestamp": time.time(),
        }

    def _file_path(self) -> str:
        return os.path.join(self.base_dir, f"{self.blueprint_id}.jsonl")

    def save_to_jsonl(self) -> str:
        path = self._file_path()
        with open(path, "a", encoding="utf-8") as f:
            for r in self._records:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        return path

    def load_from_jsonl(self) -> None:
        path = self._file_path()
        if not os.path.exists(path):
            return
        self._records.clear()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self._records.append(OperationRecord.from_dict(json.loads(line)))
