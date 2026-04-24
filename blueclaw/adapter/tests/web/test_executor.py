# -*- coding: utf-8 -*-
import os
import tempfile
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.core.operation_record import OperationLog
from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2


@pytest.fixture
def temp_dirs():
    log_dir = tempfile.mkdtemp()
    cp_dir = tempfile.mkdtemp()
    yield log_dir, cp_dir
    import shutil
    shutil.rmtree(log_dir, ignore_errors=True)
    shutil.rmtree(cp_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest.fixture
def interaction_html():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Executor Test</title></head>
    <body>
        <h1>Executor Test Page</h1>
        <input id="search-box" placeholder="Type here">
        <button id="submit-btn" onclick="document.getElementById('result').innerText='clicked'">Submit</button>
        <div id="result"></div>
        <a href="#section2" id="link1">Go to section 2</a>
        <div style="height:800px;"></div>
        <div id="section2">Section 2</div>
        <select id="dropdown">
            <option value="a">Option A</option>
            <option value="b">Option B</option>
        </select>
    </body>
    </html>
    """
    fd, path = tempfile.mkstemp(suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        yield path
    finally:
        os.remove(path)


@pytest.mark.asyncio
async def test_executor_navigate_and_screenshot(browser_page, interaction_html, temp_dirs):
    page = browser_page
    log_dir, cp_dir = temp_dirs

    op_log = OperationLog("bp-exec", base_dir=log_dir)
    cp_mgr = CheckpointManagerV2(base_dir=cp_dir)
    executor = WebExecutor(
        screenshot_capture=PlaywrightScreenshot(),
        operation_log=op_log,
        checkpoint_manager=cp_mgr,
    )

    url = f"file:///{interaction_html.replace(os.sep, '/') }"
    step = ExecutionStep(
        step_id="s1",
        name="Navigate",
        action=ActionDefinition(type="navigate", target=TargetDescription(semantic=url)),
    )

    result = await executor.execute_step(step, page, blueprint_id="bp-exec")
    assert result.status == "success"
    assert "Navigated" in result.output
    assert len(op_log.records) == 1
    rec = op_log.records[0]
    assert rec.step_id == "s1"
    assert rec.after_screenshot is not None
    assert len(rec.after_screenshot) > 0

    # 验证检查点已保存
    restored = cp_mgr.restore("bp-exec", rec.record_id)
    assert restored is not None
    assert restored.step_id == "s1"


@pytest.mark.asyncio
async def test_executor_click_and_fill(browser_page, interaction_html, temp_dirs):
    page = browser_page
    log_dir, cp_dir = temp_dirs
    url = f"file:///{interaction_html.replace(os.sep, '/') }"
    await page.goto(url)

    op_log = OperationLog("bp-exec2", base_dir=log_dir)
    cp_mgr = CheckpointManagerV2(base_dir=cp_dir)
    executor = WebExecutor(
        screenshot_capture=PlaywrightScreenshot(),
        operation_log=op_log,
        checkpoint_manager=cp_mgr,
    )

    # Fill
    step_fill = ExecutionStep(
        step_id="s2",
        name="Fill",
        action=ActionDefinition(
            type="input",
            target=TargetDescription(semantic="Type here"),
            params={"value": "hello world"},
        ),
    )
    result_fill = await executor.execute_step(step_fill, page, blueprint_id="bp-exec2")
    assert result_fill.status == "success"

    # Click
    step_click = ExecutionStep(
        step_id="s3",
        name="Click",
        action=ActionDefinition(
            type="click",
            target=TargetDescription(semantic="Submit"),
        ),
    )
    result_click = await executor.execute_step(step_click, page, blueprint_id="bp-exec2")
    assert result_click.status == "success"

    # 验证页面状态
    result_text = await page.locator("#result").inner_text()
    assert result_text == "clicked"

    # 验证记录数量
    assert len(op_log.records) == 2
    for rec in op_log.records:
        assert rec.after_screenshot is not None
        assert len(rec.after_screenshot) > 0


@pytest.mark.asyncio
async def test_executor_scroll_and_select(browser_page, interaction_html, temp_dirs):
    page = browser_page
    log_dir, cp_dir = temp_dirs
    url = f"file:///{interaction_html.replace(os.sep, '/') }"
    await page.goto(url)

    op_log = OperationLog("bp-exec3", base_dir=log_dir)
    cp_mgr = CheckpointManagerV2(base_dir=cp_dir)
    executor = WebExecutor(
        screenshot_capture=PlaywrightScreenshot(),
        operation_log=op_log,
        checkpoint_manager=cp_mgr,
    )

    # Scroll
    step_scroll = ExecutionStep(
        step_id="s4",
        name="Scroll",
        action=ActionDefinition(type="scroll", params={"dx": 0, "dy": 300}),
    )
    result_scroll = await executor.execute_step(step_scroll, page, blueprint_id="bp-exec3")
    assert result_scroll.status == "success"

    # Select
    step_select = ExecutionStep(
        step_id="s5",
        name="Select",
        action=ActionDefinition(
            type="select",
            target=TargetDescription(semantic="dropdown"),
            params={"value": "b"},
        ),
    )
    result_select = await executor.execute_step(step_select, page, blueprint_id="bp-exec3")
    assert result_select.status == "success"

    assert len(op_log.records) == 2
