# -*- coding: utf-8 -*-
import pytest
import asyncio

from blueclaw.adapter.ui.intervention.base import InterventionResult
from blueclaw.adapter.ui.intervention.cli import CliInterventionUI
from blueclaw.adapter.ui.intervention.web import WebInterventionUI
from blueclaw.adapter.ui.intervention.popup import PopupInterventionUI
from blueclaw.adapter.models import ExecutionStep, ActionDefinition


class FakeStep:
    name = "test_step"
    action = ActionDefinition(type="click")


@pytest.mark.asyncio
async def test_cli_intervention_ui_mock(monkeypatch):
    ui = CliInterventionUI()
    step = FakeStep()
    # mock input to avoid blocking
    monkeypatch.setattr("builtins.input", lambda prompt="": "replan")
    result = await ui.show(step, b"screenshot", error_info="element not found")
    assert result.choice == "replan"


@pytest.mark.asyncio
async def test_web_intervention_ui_lifecycle():
    ui = WebInterventionUI(port=18080)
    # 只测试服务启动和关闭
    await ui._start_server()
    assert ui._runner is not None
    await ui.shutdown()
    assert ui._runner is None


@pytest.mark.asyncio
async def test_web_intervention_ui_page_and_submit():
    ui = WebInterventionUI(port=18081)
    step = ExecutionStep(step_id="s1", name="ClickButton", action=ActionDefinition(type="click"))
    # 使用 _generate_page 检查 HTML 生成
    html = ui._generate_page("dummY64=", "ClickButton", "not found")
    assert "ClickButton" in html
    assert "not found" in html
    assert "canvas" in html

    # 测试 submit handler（通过 aiohttp ClientSession 发真实请求）
    await ui._start_server()
    ui._event = asyncio.Event()

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://127.0.0.1:18081/submit",
            json={"choice": "skip", "text": "ignore it", "annotation": None, "param_changes": {}},
        ) as resp:
            assert resp.status == 200

    assert ui._result is not None
    assert ui._result.choice == "skip"
    await ui.shutdown()
