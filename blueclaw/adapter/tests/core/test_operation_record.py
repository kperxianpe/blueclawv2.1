# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.core.operation_record import OperationRecord, OperationLog
from blueclaw.adapter.models import StepResult
from blueclaw.adapter.ui.intervention.base import InterventionResult


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_operation_record_serde():
    r = OperationRecord(
        record_id="r1",
        blueprint_id="bp1",
        step_id="s1",
        step_type="click",
        params={"selector": "#btn"},
        result=StepResult(status="success", output="clicked"),
        before_screenshot=b"before",
        after_screenshot=b"after",
        state_snapshot={"url": "http://test.com"},
    )
    d = r.to_dict()
    assert d["record_id"] == "r1"
    assert d["before_screenshot"] is not None
    assert d["after_screenshot"] is not None

    restored = OperationRecord.from_dict(d)
    assert restored.record_id == "r1"
    assert restored.before_screenshot == b"before"
    assert restored.after_screenshot == b"after"
    assert restored.result.status == "success"


def test_operation_log_append_and_query(temp_dir):
    log = OperationLog("bp1", base_dir=temp_dir)
    r1 = OperationRecord("r1", "bp1", "s1", "navigate")
    r2 = OperationRecord("r2", "bp1", "s2", "click")
    log.append(r1)
    log.append(r2)

    assert log.get_last_checkpoint().record_id == "r2"
    assert len(log.get_records_since("r1")) == 1
    assert log.get_records_since("r2") == []


def test_operation_log_replan_context(temp_dir):
    log = OperationLog("bp1", base_dir=temp_dir)
    r = OperationRecord("r1", "bp1", "s1", "click", state_snapshot={"url": "http://a.com"})
    intervention = InterventionResult(type="text", choice="replan", text="change selector")
    ctx = log.build_replan_context(r, intervention)
    assert ctx["checkpoint_record_id"] == "r1"
    assert ctx["intervention"]["choice"] == "replan"


def test_operation_log_persistence(temp_dir):
    log = OperationLog("bp1", base_dir=temp_dir)
    log.append(OperationRecord("r1", "bp1", "s1", "navigate"))
    log.append(OperationRecord("r2", "bp1", "s2", "click"))
    path = log.save_to_jsonl()
    assert os.path.exists(path)

    log2 = OperationLog("bp1", base_dir=temp_dir)
    log2.load_from_jsonl()
    assert len(log2.records) == 2
    assert log2.records[0].record_id == "r1"
