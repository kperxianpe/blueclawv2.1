# -*- coding: utf-8 -*-
"""
IDE 执行适配器（Week 23.5 增强版）

- 接入 IDEScreenshot
- 实现 _execute_step 带 mock 动作分发
- 返回 IDEExecutionResult
"""
import time
from typing import Dict, Any

from blueclaw.adapter.adapters.base import BaseAdapter
from blueclaw.adapter.models import (
    ExecutionBlueprint, IDEExecutionResult, StepResult,
)
from blueclaw.adapter.core.operation_record import OperationLog
from blueclaw.adapter.core.screenshot import IDEScreenshot
from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2
from blueclaw.adapter.core.replan_engine import AdapterReplanEngine
from blueclaw.adapter.ui.intervention.cli import CliInterventionUI


class IDEAdapter(BaseAdapter):
    """IDE 编辑器适配器"""

    type = "ide"

    def __init__(self):
        super().__init__(
            screenshot_capture=IDEScreenshot(),
            checkpoint_manager=CheckpointManagerV2(),
            intervention_ui=CliInterventionUI(),
            replan_engine=AdapterReplanEngine(),
        )
        self._project_path = "/tmp/project"
        self._active_file = "main.py"

    async def init(self, blueprint: ExecutionBlueprint) -> None:
        self._project_path = blueprint.config.extra.get("project_path", "/tmp/project")

    async def _execute_step(self, step, operation_log=None) -> StepResult:
        start = time.time()
        action_type = step.action.type

        if action_type == "open_file":
            self._active_file = step.action.target.semantic if step.action.target else "main.py"
            output = f"Opened {self._active_file}"
            status = "success"
        elif action_type == "edit_file":
            output = f"Edited {self._active_file}"
            status = "success"
        elif action_type == "execute_command":
            cmd = step.action.params.get("command", "")
            output = f"Executed command: {cmd}"
            status = "success"
        else:
            output = f"Mock IDE action: {action_type}"
            status = "success"

        if step.action.params.get("force_fail"):
            status = "failed"
            output = "Forced IDE failure for intervention test"

        return StepResult(
            status=status,
            output=output,
            error=output if status == "failed" else None,
            duration_ms=(time.time() - start) * 1000,
            needs_intervention=(status == "failed"),
        )

    async def _capture_screenshot(self) -> bytes:
        return await self.screenshot_capture.capture(
            project_path=self._project_path,
            active_file=self._active_file,
        )

    def _get_state_snapshot(self, blueprint, current_index: int) -> Dict[str, Any]:
        return {
            "adapter_type": "ide",
            "project_path": self._project_path,
            "active_file": self._active_file,
            "current_step_index": current_index,
            "remaining_steps": [s.model_dump() for s in blueprint.steps],
            "config": blueprint.config.model_dump(),
        }

    def _build_partial_result(
        self, operation_log: OperationLog, blueprint, status: str, error=None
    ):
        total_ms = sum(r.result.duration_ms for r in operation_log.records)
        modified = list({r.step_id for r in operation_log.records if r.step_type == "edit_file"})
        return IDEExecutionResult(
            success=(status == "completed"),
            duration_ms=total_ms,
            output=f"IDE execution {status}, records={len(operation_log.records)}",
            modified_files=modified,
            error_context={"error": error, "status": status} if error else None,
        )

    async def pause(self) -> None:
        self._paused = True

    async def resume(self) -> None:
        self._paused = False

    async def cleanup(self) -> None:
        pass
