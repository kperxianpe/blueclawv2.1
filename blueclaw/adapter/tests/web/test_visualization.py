# -*- coding: utf-8 -*-
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from blueclaw.adapter.web.visualization import CanvasMindVisualizer
from blueclaw.adapter.web.models import WebElement


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest.fixture
def visualizer():
    return CanvasMindVisualizer()


@pytest.mark.asyncio
async def test_inject_overlay(browser_page, visualizer):
    page = browser_page
    await page.set_content("<html><body><h1>Test</h1></body></html>")
    await visualizer.inject_overlay(page)
    style = await page.evaluate("() => !!document.getElementById('blueclaw-style')")
    assert style is True


@pytest.mark.asyncio
async def test_mark_operation(browser_page, visualizer):
    page = browser_page
    await page.set_content("<html><body><h1>Test</h1></body></html>")
    await visualizer.inject_overlay(page)
    elem = WebElement(
        id="btn", tag="button",
        normalized_coords={"x": 0.5, "y": 0.5, "width": 0.1, "height": 0.05}
    )
    await visualizer.mark_operation(page, elem, "click")
    marks = await page.evaluate("() => document.querySelectorAll('.blueclaw-op-mark').length")
    assert marks >= 1


@pytest.mark.asyncio
async def test_mark_checkpoint(browser_page, visualizer):
    page = browser_page
    await page.set_content("<html><body><h1>Test</h1></body></html>")
    await visualizer.inject_overlay(page)
    elem = WebElement(
        id="cp", tag="div",
        normalized_coords={"x": 0.1, "y": 0.1, "width": 0.05, "height": 0.05}
    )
    await visualizer.mark_checkpoint(page, elem)
    flags = await page.evaluate("() => document.querySelectorAll('.blueclaw-cp-flag').length")
    assert flags >= 1


@pytest.mark.asyncio
async def test_highlight_distractions(browser_page, visualizer):
    page = browser_page
    await page.set_content("<html><body><h1>Test</h1></body></html>")
    await visualizer.inject_overlay(page)
    distractions = [
        WebElement(
            id="ad1", tag="div",
            normalized_coords={"x": 0, "y": 0, "width": 1, "height": 0.1}
        ),
    ]
    await visualizer.highlight_distractions(page, distractions)
    overlays = await page.evaluate("() => document.querySelectorAll('.blueclaw-distraction').length")
    assert overlays >= 1


@pytest.mark.asyncio
async def test_show_progress(browser_page, visualizer):
    page = browser_page
    await page.set_content("<html><body><h1>Test</h1></body></html>")
    await visualizer.show_progress(page, current_step=2, total_steps=5, duration_ms=1500)
    bar = await page.evaluate("() => !!document.getElementById('blueclaw-progress')")
    assert bar is True
    text = await page.evaluate("() => document.getElementById('blueclaw-progress-text').textContent")
    assert "Step 2/5" in text


@pytest.mark.asyncio
async def test_clear_overlays(browser_page, visualizer):
    page = browser_page
    await page.set_content("<html><body><h1>Test</h1></body></html>")
    await visualizer.inject_overlay(page)
    await visualizer.show_progress(page, 1, 3, 0)
    await visualizer.mark_checkpoint(page)
    await visualizer.clear_overlays(page)
    remaining = await page.evaluate("() => document.querySelectorAll('[data-blueclaw]').length")
    assert remaining == 0
    bar = await page.evaluate("() => !!document.getElementById('blueclaw-progress')")
    assert bar is False
    style = await page.evaluate("() => !!document.getElementById('blueclaw-style')")
    assert style is False
