# -*- coding: utf-8 -*-
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from blueclaw.adapter.web.recovery import RecoveryController, RecoveryConfig
from blueclaw.adapter.web.checkpoint import WebCheckpointManager
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest.fixture
def cp_manager(tmp_path):
    return WebCheckpointManager(base_dir=str(tmp_path))


@pytest.fixture
def executor():
    return WebExecutor(screenshot_capture=PlaywrightScreenshot())


@pytest.mark.asyncio
async def test_recovery_retry_succeeds(browser_page, cp_manager, executor):
    page = browser_page
    await page.set_content("<html><body><button id='btn'>Click</button></body></html>")

    rc = RecoveryController(
        web_checkpoint_manager=cp_manager,
        config=RecoveryConfig(max_retries=2, retry_backoff_ms=100),
    )

    step = ExecutionStep(
        step_id="s1",
        name="Click",
        action=ActionDefinition(type="click", target=TargetDescription(selector="#btn")),
    )

    # 第一次执行成功，不需要恢复
    result = await executor.execute_step(step, page, blueprint_id="bp-r1")
    assert result.status == "success"


@pytest.mark.asyncio
async def test_recovery_fallback_selector(browser_page, cp_manager, executor):
    page = browser_page
    await page.set_content("<html><body><button id='real'>Real</button></body></html>")

    rc = RecoveryController(
        web_checkpoint_manager=cp_manager,
        config=RecoveryConfig(
            max_retries=0,
            fallback_selectors=["#real"],
        ),
    )

    # 步骤使用不存在的选择器，fallback 使用 #real
    step = ExecutionStep(
        step_id="s1",
        name="Click",
        action=ActionDefinition(type="click", target=TargetDescription(selector="#missing")),
    )

    action = await rc.recover(page, step, "Element not found", "bp-r2", executor)
    assert action.action == "fallback"
    assert "#real" in action.message


@pytest.mark.asyncio
async def test_recovery_rollback(browser_page, cp_manager, executor):
    page = browser_page
    await page.goto("about:blank")
    await page.set_content("<html><body><div id='orig'>Original</div></body></html>")

    # 先保存检查点
    cp = await cp_manager.save(page, "bp-r3", "s0")

    # 修改页面
    await page.evaluate("() => { document.body.innerHTML = '<p>Changed</p>'; }")

    rc = RecoveryController(
        web_checkpoint_manager=cp_manager,
        config=RecoveryConfig(max_retries=0, fallback_selectors=[], enable_rollback=True),
    )

    step = ExecutionStep(
        step_id="s1",
        name="Click",
        action=ActionDefinition(type="click", target=TargetDescription(selector="#missing")),
    )

    action = await rc.recover(page, step, "Element not found", "bp-r3", executor)
    assert action.action == "rollback"
    # 验证页面已恢复
    restored_html = await page.content()
    assert "Original" in restored_html or "orig" in restored_html


@pytest.mark.asyncio
async def test_recovery_pause_when_exhausted(browser_page, cp_manager, executor):
    page = browser_page
    await page.set_content("<html><body></body></html>")

    rc = RecoveryController(
        web_checkpoint_manager=cp_manager,
        config=RecoveryConfig(max_retries=0, fallback_selectors=[], enable_rollback=False),
    )

    step = ExecutionStep(
        step_id="s1",
        name="Click",
        action=ActionDefinition(type="click", target=TargetDescription(selector="#missing")),
    )

    action = await rc.recover(page, step, "Element not found", "bp-r4", executor)
    assert action.action == "pause"
    assert "exhausted" in action.message


@pytest.mark.asyncio
async def test_recovery_retry_exhausts_then_fallback(browser_page, cp_manager, executor):
    page = browser_page
    await page.set_content("<html><body><button id='fb'>Fallback</button></body></html>")

    rc = RecoveryController(
        web_checkpoint_manager=cp_manager,
        config=RecoveryConfig(
            max_retries=1,
            retry_backoff_ms=100,
            fallback_selectors=["#fb"],
            enable_rollback=False,
        ),
    )

    step = ExecutionStep(
        step_id="s1",
        name="Click",
        action=ActionDefinition(type="click", target=TargetDescription(selector="#missing")),
    )

    action = await rc.recover(page, step, "Element not found", "bp-r5", executor)
    # 重试 1 次失败，fallback 成功
    assert action.action == "fallback"
