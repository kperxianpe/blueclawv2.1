# -*- coding: utf-8 -*-
"""
Adapter 基类（Week 23.5 增强版）

- 支持强制截图、操作记录、检查点保存、干预闭环
"""
import time
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from blueclaw.adapter.models import ExecutionBlueprint, ExecutionResult, StepResult
from blueclaw.adapter.core.operation_record import OperationRecord, OperationLog
from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2
from blueclaw.adapter.core.screenshot import ScreenshotCapture
from blueclaw.adapter.core.replan_engine import AdapterReplanEngine
from blueclaw.adapter.ui.intervention.base import InterventionUI, InterventionResult


class BaseAdapter(ABC):
    """执行适配器基类"""

    type: str = ""

    def __init__(
        self,
        screenshot_capture: Optional[ScreenshotCapture] = None,
        checkpoint_manager: Optional[CheckpointManagerV2] = None,
        intervention_ui: Optional[InterventionUI] = None,
        replan_engine: Optional[AdapterReplanEngine] = None,
    ):
        self.screenshot_capture = screenshot_capture
        self.checkpoint_manager = checkpoint_manager or CheckpointManagerV2()
        self.intervention_ui = intervention_ui
        self.replan_engine = replan_engine or AdapterReplanEngine()
        self._paused = False

    @abstractmethod
    async def init(self, blueprint: ExecutionBlueprint) -> None:
        """初始化适配器环境"""
        ...

    async def execute(self, blueprint: ExecutionBlueprint) -> ExecutionResult:
        """执行蓝图（带截图/记录/检查点/干预闭环）"""
        operation_log = OperationLog(blueprint.task_id)
        final_result: Optional[ExecutionResult] = None

        for i, step in enumerate(blueprint.steps):
            if self._paused:
                break

            # 子类（如 WebAdapter）可能在 _execute_step 内部自行处理截图和记录
            # 为了兼容，先调用 _execute_step，然后检查是否需要补充记录
            t0 = time.time()
            step_result = await self._execute_step(step, operation_log)
            duration = (time.time() - t0) * 1000

            # 如果 operation_log 中没有新增记录，说明是旧式适配器，需要在这里补充创建
            record_created_here = False
            if not operation_log.records or operation_log.records[-1].step_id != step.step_id:
                # 1. 执行前截图（可选）
                before_ss = await self._capture_screenshot() if self.screenshot_capture else None

                # 2. 执行后截图（强制，如果配置了截图器）
                after_ss = b""
                if self.screenshot_capture:
                    raw_ss = await self._capture_screenshot()
                    after_ss = self.screenshot_capture.compress(raw_ss, quality=80)

                # 3. 创建操作记录
                record = OperationRecord(
                    record_id=f"rec_{uuid.uuid4().hex[:8]}",
                    blueprint_id=blueprint.task_id,
                    step_id=step.step_id,
                    step_type=step.action.type,
                    params=step.action.params,
                    result=step_result,
                    before_screenshot=before_ss,
                    after_screenshot=after_ss or None,
                    timestamp=time.time(),
                    state_snapshot=self._get_state_snapshot(blueprint, i),
                )
                operation_log.append(record)
                record_created_here = True

                # 4. 保存检查点
                if self.checkpoint_manager:
                    await self._save_checkpoint_async(record)

            # 获取当前步骤对应的记录（用于干预和 replan）
            current_record = [r for r in operation_log.records if r.step_id == step.step_id][-1]
            after_ss_for_ui = current_record.after_screenshot or b""

            # 5. 检查是否需要干预
            if step_result.needs_intervention or step_result.status == "failed":
                if self.intervention_ui:
                    intervention = await self.intervention_ui.show(
                        step, after_ss_for_ui, step_result.error
                    )
                    current_record.has_intervention = True
                    current_record.intervention_type = intervention.choice

                    # 处理干预结果
                    if intervention.choice == "replan":
                        new_bp = self.replan_engine.replan_from_checkpoint(current_record, intervention)
                        blueprint = self.replan_engine.merge_blueprint(blueprint, new_bp, step.step_id)
                        final_result = self._build_partial_result(operation_log, blueprint, "replan")
                        break
                    elif intervention.choice == "retry":
                        step.action.params.update(intervention.param_changes)
                        continue
                    elif intervention.choice == "skip":
                        step_result.status = "skipped"
                        continue
                    elif intervention.choice == "abort":
                        final_result = self._build_partial_result(
                            operation_log, blueprint, "aborted", error=step_result.error
                        )
                        break

        if final_result is None:
            final_result = self._build_partial_result(operation_log, blueprint, "completed")

        return final_result

    @abstractmethod
    async def _execute_step(self, step, operation_log: Optional[OperationLog] = None) -> StepResult:
        """执行单个步骤（子类实现）"""
        ...

    @abstractmethod
    async def _capture_screenshot(self) -> bytes:
        """捕获当前环境截图（子类实现）"""
        ...

    @abstractmethod
    def _get_state_snapshot(self, blueprint: ExecutionBlueprint, current_index: int) -> Dict[str, Any]:
        """获取可序列化状态快照（子类实现）"""
        ...

    async def _save_checkpoint_async(self, record: OperationRecord) -> None:
        """异步保存检查点（实际调用同步文件操作，用线程池避免阻塞）"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.checkpoint_manager.save_from_record, record)

    def _build_partial_result(
        self,
        operation_log: OperationLog,
        blueprint: ExecutionBlueprint,
        status: str,
        error: Optional[str] = None,
    ) -> ExecutionResult:
        """构建执行结果（由子类覆写以返回 WebExecutionResult 或 IDEExecutionResult）"""
        # 默认返回一个基础 ExecutionResult（子类应覆写此方法返回具体类型）
        from blueclaw.adapter.models import WebExecutionResult
        return WebExecutionResult(
            success=(status == "completed"),
            duration_ms=0.0,
            output=f"Execution status: {status}, records: {len(operation_log.records)}",
            error_context={"error": error, "status": status} if error else None,
        )

    @abstractmethod
    async def pause(self) -> None:
        """暂停执行"""
        ...

    @abstractmethod
    async def resume(self) -> None:
        """恢复执行"""
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        ...
