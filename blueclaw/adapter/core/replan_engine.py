# -*- coding: utf-8 -*-
"""
AdapterReplanEngine - 基于检查点和干预的重新规划引擎

与 blueclaw/core/replan_engine.py（旧 Core 层引擎）隔离。
"""
import copy
from typing import Dict, Any, List, Optional

from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition
from blueclaw.adapter.core.operation_record import OperationRecord
from blueclaw.adapter.ui.intervention.base import InterventionResult


class AdapterReplanEngine:
    """Adapter 层重新规划引擎"""

    def replan_from_checkpoint(
        self,
        record: OperationRecord,
        intervention: InterventionResult,
    ) -> ExecutionBlueprint:
        """
        基于检查点记录和用户干预生成新蓝图。
        当前为简化实现：根据干预内容修改当前步骤参数并生成后续步骤。
        """
        context = self._build_context(record, intervention)

        # 读取原蓝图的 steps 上下文（从 state_snapshot 中恢复，dict -> ExecutionStep）
        raw_steps = context.get("original_steps", [])
        original_steps = [ExecutionStep.model_validate(s) for s in raw_steps]
        current_step_id = record.step_id

        # 拆分：步骤 before_current, current_step, after_current
        before_steps: List[ExecutionStep] = []
        current_step: Optional[ExecutionStep] = None
        after_steps: List[ExecutionStep] = []

        found = False
        for s in original_steps:
            if found:
                after_steps.append(copy.deepcopy(s))
                continue
            if s.step_id == current_step_id:
                current_step = copy.deepcopy(s)
                found = True
            else:
                before_steps.append(copy.deepcopy(s))

        if not found:
            current_step = self._step_from_record(record)

        new_steps: List[ExecutionStep] = list(before_steps)

        if intervention.choice == "retry":
            # 修改当前步骤参数并保留
            if intervention.param_changes:
                current_step.action.params.update(intervention.param_changes)
            if intervention.text and "改" in intervention.text and "selector" in str(intervention.text):
                current_step.action.params["user_hint"] = intervention.text
            if intervention.annotation:
                current_step.action.params["user_annotation"] = intervention.annotation
            new_steps.append(current_step)
            new_steps.extend(after_steps)

        elif intervention.choice == "replan":
            # 保留当前步骤 + 插入修复步骤 + 保留后续步骤
            if intervention.param_changes:
                current_step.action.params.update(intervention.param_changes)
            if intervention.annotation:
                current_step.action.params["user_annotation"] = intervention.annotation
            new_steps.append(current_step)
            fix_step = ExecutionStep(
                step_id=f"{current_step_id}_fix",
                name="自适应修复",
                action=ActionDefinition(
                    type="wait",
                    params={"reason": intervention.text or "用户触发重新规划", "annotation": intervention.annotation},
                ),
            )
            new_steps.append(fix_step)
            new_steps.extend(after_steps)

        elif intervention.choice == "skip":
            # 跳过当前步骤，直接保留后续步骤
            new_steps.extend(after_steps)

        else:
            # 默认 fallback（如 abort 等）：保留当前步骤
            new_steps.append(current_step)
            new_steps.extend(after_steps)

        return ExecutionBlueprint(
            task_id=record.blueprint_id,
            adapter_type=context.get("adapter_type", "web"),
            steps=new_steps,
            config=context.get("config", {}),
        )

    def merge_blueprint(
        self,
        original: ExecutionBlueprint,
        new_blueprint: ExecutionBlueprint,
        from_step_id: str,
    ) -> ExecutionBlueprint:
        """
        合并新蓝图到原蓝图：保留已完成步骤，替换从 from_step_id 开始的后续步骤。
        """
        kept_steps: List[ExecutionStep] = []
        for s in original.steps:
            if s.step_id == from_step_id:
                break
            kept_steps.append(copy.deepcopy(s))

        # 找到 new_blueprint 中 from_step_id 对应的位置，从这里开始拼接
        found = False
        for s in new_blueprint.steps:
            if found:
                kept_steps.append(copy.deepcopy(s))
            if s.step_id == from_step_id:
                found = True
                kept_steps.append(copy.deepcopy(s))

        # 如果没找到，说明 new_blueprint 是全新列表，直接全部追加
        if not found:
            kept_steps.extend([copy.deepcopy(s) for s in new_blueprint.steps])

        return ExecutionBlueprint(
            task_id=original.task_id,
            adapter_type=original.adapter_type,
            steps=kept_steps,
            config=original.config,
        )

    def _build_context(self, record: OperationRecord, intervention: InterventionResult) -> Dict[str, Any]:
        return {
            "blueprint_id": record.blueprint_id,
            "step_id": record.step_id,
            "state_snapshot": record.state_snapshot,
            "intervention_text": intervention.text,
            "intervention_choice": intervention.choice,
            "intervention_annotation": intervention.annotation,
            "original_steps": record.state_snapshot.get("remaining_steps", []),
            "adapter_type": record.state_snapshot.get("adapter_type", "web"),
            "config": record.state_snapshot.get("config", {}),
        }

    def _step_from_record(self, record: OperationRecord) -> ExecutionStep:
        return ExecutionStep(
            step_id=record.step_id,
            name=f"恢复步骤 {record.step_id}",
            action=ActionDefinition(
                type=record.step_type or "wait",
                params=record.params,
            ),
        )
