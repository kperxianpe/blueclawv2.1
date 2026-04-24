# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2
from blueclaw.adapter.core.operation_record import OperationRecord
from blueclaw.adapter.models import StepResult


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_save_and_restore(temp_dir):
    cm = CheckpointManagerV2(base_dir=temp_dir)
    r = OperationRecord("r1", "bp1", "s1", "click", result=StepResult(status="success"), after_screenshot=b"ss")
    path = cm.save_from_record(r)
    assert os.path.exists(path)

    restored = cm.restore("bp1", "r1")
    assert restored is not None
    assert restored.record_id == "r1"
    assert restored.after_screenshot == b"ss"


def test_list_and_cleanup(temp_dir):
    cm = CheckpointManagerV2(base_dir=temp_dir)
    for i in range(5):
        r = OperationRecord(f"r{i}", "bp1", f"s{i}", "click")
        cm.save_from_record(r)

    cps = cm.list_checkpoints("bp1")
    assert len(cps) == 5

    removed = cm.cleanup("bp1", keep_last_n=2)
    assert removed == 3
    assert len(cm.list_checkpoints("bp1")) == 2


def test_delete_all(temp_dir):
    cm = CheckpointManagerV2(base_dir=temp_dir)
    cm.save_from_record(OperationRecord("r1", "bp1", "s1", "click"))
    cm.delete_all("bp1")
    assert not os.path.exists(os.path.join(temp_dir, "bp1"))
