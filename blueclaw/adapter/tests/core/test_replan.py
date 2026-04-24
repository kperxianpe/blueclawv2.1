# -*- coding: utf-8 -*-
import pytest

from blueclaw.adapter.core.replan_engine import AdapterReplanEngine
from blueclaw.adapter.core.operation_record import OperationRecord
from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ActionDefinition, StepResult
from blueclaw.adapter.ui.intervention.base import InterventionResult


def make_blueprint():
    return ExecutionBlueprint(
        task_id="bp1",
        adapter_type="web",
        steps=[
            ExecutionStep(step_id="s1", name="Nav", action=ActionDefinition(type="navigate")),
            ExecutionStep(step_id="s2", name="Click", action=ActionDefinition(type="click")),
            ExecutionStep(step_id="s3", name="Input", action=ActionDefinition(type="input")),
        ],
    )


def make_record(step_id="s2"):
    bp = make_blueprint()
    return OperationRecord(
        record_id="rec1",
        blueprint_id="bp1",
        step_id=step_id,
        step_type="click",
        result=StepResult(status="failed"),
        state_snapshot={
            "remaining_steps": [s.model_dump() for s in bp.steps],
            "adapter_type": "web",
        },
    )


def test_replan_from_checkpoint_replan():
    engine = AdapterReplanEngine()
    record = make_record("s2")
    intervention = InterventionResult(type="text", choice="replan", text="change button")
    new_bp = engine.replan_from_checkpoint(record, intervention)

    ids = [s.step_id for s in new_bp.steps]
    assert "s1" in ids          # 保留已完成步骤
    assert "s2" in ids          # 当前步骤保留
    assert "s2_fix" in ids      # 生成修复步骤
    assert "s3" in ids          # 后续步骤保留


def test_replan_from_checkpoint_skip():
    engine = AdapterReplanEngine()
    record = make_record("s2")
    intervention = InterventionResult(type="button", choice="skip")
    new_bp = engine.replan_from_checkpoint(record, intervention)

    ids = [s.step_id for s in new_bp.steps]
    assert "s1" in ids
    assert "s2" not in ids      # 跳过当前步骤
    assert "s3" in ids


def test_replan_from_checkpoint_retry_params():
    engine = AdapterReplanEngine()
    record = make_record("s2")
    intervention = InterventionResult(type="button", choice="retry", param_changes={"selector": "#new"})
    new_bp = engine.replan_from_checkpoint(record, intervention)

    s2 = [s for s in new_bp.steps if s.step_id == "s2"][0]
    assert s2.action.params["selector"] == "#new"


def test_merge_blueprint():
    engine = AdapterReplanEngine()
    original = make_blueprint()
    new_bp = ExecutionBlueprint(
        task_id="bp1",
        adapter_type="web",
        steps=[
            ExecutionStep(step_id="s2", name="ClickNew", action=ActionDefinition(type="click")),
            ExecutionStep(step_id="s3_new", name="InputNew", action=ActionDefinition(type="input")),
        ],
    )
    merged = engine.merge_blueprint(original, new_bp, "s2")
    ids = [s.step_id for s in merged.steps]
    assert ids == ["s1", "s2", "s3_new"]
