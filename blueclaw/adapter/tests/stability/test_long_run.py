# -*- coding: utf-8 -*-
"""
稳定性测试 - 长时间运行

- 连续执行多个任务
- 状态机持久化稳定性
- 重复操作一致性
"""
import pytest

from blueclaw.adapter.state import StateMachine, AdapterState, FileStatePersistence


@pytest.fixture
def persistence():
    return FileStatePersistence()


@pytest.mark.asyncio
async def test_state_machine_50_transitions(persistence):
    """连续 50 次状态转换稳定性"""
    sm = StateMachine(task_id="stability_50", persistence=persistence)

    transitions = [
        (AdapterState.PLANNING, {"action": "init"}),
        (AdapterState.EXECUTING, {"action": "execute"}),
        (AdapterState.VALIDATING, {"action": "validate"}),
        (AdapterState.COMPLETED, {"action": "finish"}),
    ]

    for i in range(50):
        sm = StateMachine(task_id=f"stability_run_{i}", persistence=persistence)
        for state, meta in transitions:
            await sm.transition(state, meta)
        assert sm.current == AdapterState.COMPLETED


def test_file_persistence_rapid_save_load(persistence, tmp_path):
    """快速保存/加载 100 次"""
    from blueclaw.adapter.state import AdapterState

    for i in range(100):
        history = [{"iteration": i, "data": "x" * 1000}]
        persistence.save(f"task_{i}", AdapterState.EXECUTING, history)
        loaded = persistence.load(f"task_{i}")
        assert loaded is not None
        assert loaded["history"][0]["iteration"] == i


@pytest.mark.asyncio
async def test_repeated_analyze_consistency():
    """重复分析同一项目，结果一致"""
    import tempfile
    import os

    path = tempfile.mkdtemp()
    try:
        with open(os.path.join(path, "main.py"), "w") as f:
            f.write("def foo(): pass\n")

        from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer(path)

        results = [analyzer.analyze() for _ in range(10)]

        # 所有结果应一致
        first = results[0]
        for r in results[1:]:
            assert r.total_files == first.total_files
            assert r.total_lines == first.total_lines
            assert r.languages == first.languages
    finally:
        import shutil
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.asyncio
async def test_checkpoint_save_load_stability():
    """检查点保存/加载 20 次循环"""
    import tempfile
    import os
    from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2

    path = tempfile.mkdtemp()
    try:
        cm = CheckpointManagerV2(base_dir=path)
        from blueclaw.adapter.core.operation_record import OperationRecord, StepResult
        for i in range(20):
            record = OperationRecord(
                record_id=f"rec_{i}",
                blueprint_id="test",
                step_id=f"step_{i}",
                step_type="navigate",
                params={},
                result=StepResult(status="success", output="ok"),
                timestamp=12345.0 + i,
            )
            cm.save_from_record(record)

        records = cm.list_checkpoints("test")
        assert len(records) == 20
    finally:
        import shutil
        shutil.rmtree(path, ignore_errors=True)
