# -*- coding: utf-8 -*-
import os
import tempfile
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from blueclaw.adapter.web.analyzer import WebAnalyzer
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest.fixture
def sample_html():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Welcome</h1>
        <button id="btn1" class="primary">Click Me</button>
        <input type="text" name="search" placeholder="Search here" aria-label="Search box">
        <a href="/link">Go to link</a>
        <div style="display:none"><button>Hidden</button></div>
        <select id="dropdown">
            <option>A</option>
            <option>B</option>
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
async def test_analyzer_extracts_elements(browser_page, sample_html):
    page = browser_page
    await page.goto(f"file:///{sample_html.replace(os.sep, '/')}")

    analyzer = WebAnalyzer(screenshot_capture=PlaywrightScreenshot())
    analysis = await analyzer.analyze(page)

    assert analysis.url == f"file:///{sample_html.replace(os.sep, '/') }"
    assert analysis.title == "Test Page"
    assert analysis.viewport_width == 1280
    assert analysis.viewport_height == 720
    assert len(analysis.screenshot) > 0

    tags = [e.tag for e in analysis.elements]
    assert "button" in tags
    assert "input" in tags
    assert "a" in tags
    assert "select" in tags

    # 隐藏按钮不应被提取
    texts = [e.text for e in analysis.elements]
    assert "Hidden" not in texts


@pytest.mark.asyncio
async def test_analyzer_normalized_coords(browser_page, sample_html):
    page = browser_page
    await page.goto(f"file:///{sample_html.replace(os.sep, '/')}")

    analyzer = WebAnalyzer(screenshot_capture=PlaywrightScreenshot())
    analysis = await analyzer.analyze(page)

    for elem in analysis.elements:
        nc = elem.normalized_coords
        assert 0.0 <= nc["x"] <= 1.0
        assert 0.0 <= nc["y"] <= 1.0
        assert 0.0 <= nc["width"] <= 1.0
        assert 0.0 <= nc["height"] <= 1.0
        assert elem.bbox["width"] > 0
        assert elem.bbox["height"] > 0


@pytest.mark.asyncio
async def test_analyzer_semantic_fields(browser_page, sample_html):
    page = browser_page
    await page.goto(f"file:///{sample_html.replace(os.sep, '/')}")

    analyzer = WebAnalyzer(screenshot_capture=PlaywrightScreenshot())
    analysis = await analyzer.analyze(page)

    inputs = [e for e in analysis.elements if e.tag == "input"]
    assert len(inputs) >= 1
    inp = inputs[0]
    assert inp.placeholder == "Search here"
    assert inp.aria_label == "Search box"
    assert inp.attributes.get("name") == "search"
