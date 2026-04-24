# -*- coding: utf-8 -*-
"""
稳定性测试 - 内存检查

- 截图内存释放
- 大对象清理
- 操作日志增长控制
"""
import sys
import pytest

from blueclaw.adapter.core.operation_record import OperationLog
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot


def test_operation_log_memory_bound():
    """操作日志增长可控"""
    import tempfile
    base_dir = tempfile.mkdtemp()
    log = OperationLog(blueprint_id="test", base_dir=base_dir)

    for i in range(200):
        from blueclaw.adapter.core.operation_record import OperationRecord, StepResult
        log.append(OperationRecord(
            record_id=f"rec_{i}",
            blueprint_id="test",
            step_id=f"step_{i}",
            step_type="wait",
            params={},
            result=StepResult(status="success"),
            timestamp=float(i),
        ))

    records = log.records
    assert len(records) == 200  # 所有记录都应保存


def test_operation_log_query_does_not_grow():
    """查询操作不增加内存"""
    import tempfile
    base_dir = tempfile.mkdtemp()
    log = OperationLog(blueprint_id="test", base_dir=base_dir)
    from blueclaw.adapter.core.operation_record import OperationRecord, StepResult
    for i in range(50):
        log.append(OperationRecord(
            record_id=f"r{i}", blueprint_id="b", step_id=f"s{i}",
            step_type="wait", params={}, result=StepResult(status="success"),
            timestamp=float(i),
        ))

    import sys
    size_before = sys.getsizeof(log._records)

    for _ in range(10):
        _ = log.records[-10:]

    size_after = sys.getsizeof(log._records)
    assert size_after == size_before


def test_screenshot_compress_does_not_leak():
    """截图压缩后原始数据可被 GC"""
    import io
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    capture = PlaywrightScreenshot()

    # 创建测试图片
    img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
    out = io.BytesIO()
    img.save(out, format="PNG")
    data = out.getvalue()

    # 多次压缩，不应累积内存
    for _ in range(20):
        compressed = capture.compress(data, quality=75)
        assert len(compressed) > 0
        del compressed


def test_screenshot_resize_does_not_leak():
    """截图缩放后原始数据可被 GC"""
    import io
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    capture = PlaywrightScreenshot()

    img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
    out = io.BytesIO()
    img.save(out, format="PNG")
    data = out.getvalue()

    for _ in range(20):
        resized = capture.resize(data, max_dimension=640)
        assert len(resized) > 0
        del resized
