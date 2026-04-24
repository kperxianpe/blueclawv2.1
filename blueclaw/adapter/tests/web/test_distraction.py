# -*- coding: utf-8 -*-
import os
import tempfile
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from blueclaw.adapter.web.analyzer import WebAnalyzer
from blueclaw.adapter.web.distraction import DistractionDetector
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest.fixture
def distraction_html():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Distraction Test</title></head>
    <body>
        <div id="content">
            <button id="real-btn">Real Button</button>
            <input placeholder="Search">
        </div>
        <div id="ad-banner" style="position:fixed;top:0;left:0;width:100%;height:50px;background:red;">
            Advertisement
        </div>
        <div id="popup" style="position:fixed;bottom:10px;right:10px;width:200px;height:100px;background:blue;">
            Subscribe now!
        </div>
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
async def test_detect_distractions(browser_page, distraction_html):
    page = browser_page
    await page.goto(f"file:///{distraction_html.replace(os.sep, '/')}")

    analyzer = WebAnalyzer(screenshot_capture=PlaywrightScreenshot())
    analysis = await analyzer.analyze(page)

    detector = DistractionDetector(variance_threshold=5.0)
    distractions = detector.detect(
        analysis.elements,
        analysis.screenshot,
        {"width": analysis.viewport_width, "height": analysis.viewport_height},
    )

    distraction_ids = {d.id for d in distractions}
    assert "ad-banner" in distraction_ids or any("ad" in d.id for d in distractions)
    assert "popup" in distraction_ids or any("popup" in d.id for d in distractions)

    # 正常按钮不应被标记
    for d in distractions:
        assert d.id != "real-btn"


@pytest.mark.asyncio
async def test_normal_elements_not_distractions(browser_page, distraction_html):
    page = browser_page
    await page.goto(f"file:///{distraction_html.replace(os.sep, '/')}")

    analyzer = WebAnalyzer(screenshot_capture=PlaywrightScreenshot())
    analysis = await analyzer.analyze(page)

    detector = DistractionDetector()
    detector.detect(
        analysis.elements,
        analysis.screenshot,
        {"width": analysis.viewport_width, "height": analysis.viewport_height},
    )

    real_btn = [e for e in analysis.elements if e.id == "real-btn"]
    if real_btn:
        assert real_btn[0].is_distraction is False
