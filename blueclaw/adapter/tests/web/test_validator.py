# -*- coding: utf-8 -*-
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from blueclaw.adapter.web.validator import WebValidator, ValidationResult
from blueclaw.adapter.models import ValidationRule
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest.fixture
def validator():
    return WebValidator(screenshot_capture=PlaywrightScreenshot(), timeout=5)


@pytest.mark.asyncio
async def test_validate_url_match_pass(browser_page, validator):
    page = browser_page
    await page.goto("https://example.com/path")
    rule = ValidationRule(type="url_match", expected=r"example\.com")
    result = await validator.validate(page, rule)
    assert result.success is True
    assert result.type == "url_match"


@pytest.mark.asyncio
async def test_validate_url_match_fail(browser_page, validator):
    page = browser_page
    await page.goto("https://example.com/path")
    rule = ValidationRule(type="url_match", expected=r"google\.com")
    result = await validator.validate(page, rule)
    assert result.success is False


@pytest.mark.asyncio
async def test_validate_presence_pass(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body><div id='target'>Hi</div></body></html>")
    rule = ValidationRule(type="presence", expected="#target")
    result = await validator.validate(page, rule)
    assert result.success is True
    assert result.details["count"] == 1


@pytest.mark.asyncio
async def test_validate_presence_fail(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body><div id='other'>Hi</div></body></html>")
    rule = ValidationRule(type="presence", expected="#missing")
    result = await validator.validate(page, rule)
    assert result.success is False


@pytest.mark.asyncio
async def test_validate_text_contains_pass(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body><div id='msg'>Welcome aboard</div></body></html>")
    rule = ValidationRule(type="text_contains", expected={"selector": "#msg", "text": "Welcome"})
    result = await validator.validate(page, rule)
    assert result.success is True


@pytest.mark.asyncio
async def test_validate_text_contains_fail(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body><div id='msg'>Goodbye</div></body></html>")
    rule = ValidationRule(type="text_contains", expected={"selector": "#msg", "text": "Welcome"})
    result = await validator.validate(page, rule)
    assert result.success is False


@pytest.mark.asyncio
async def test_validate_text_contains_no_selector(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body><p>Hello world</p></body></html>")
    rule = ValidationRule(type="text_contains", expected="world")
    result = await validator.validate(page, rule)
    assert result.success is True


@pytest.mark.asyncio
async def test_validate_visual_match_pass(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body style='background:#fff'><h1>Title</h1></body></html>")
    # 先捕获基准截图
    baseline = await validator.screenshot_capture.capture(page)
    rule = ValidationRule(type="visual_match", expected=baseline)
    result = await validator.validate(page, rule, context={"ssim_threshold": 0.9})
    assert result.success is True
    assert result.details["ssim"] > 0.9


@pytest.mark.asyncio
async def test_validate_visual_match_fail(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body style='background:#fff'><h1>Title</h1></body></html>")
    baseline = await validator.screenshot_capture.capture(page)
    # 改变页面内容
    await page.set_content("<html><body style='background:#000'><h1>Different</h1></body></html>")
    rule = ValidationRule(type="visual_match", expected=baseline)
    result = await validator.validate(page, rule, context={"ssim_threshold": 0.9})
    assert result.success is False
    assert result.details["ssim"] < 0.9


@pytest.mark.asyncio
async def test_validate_custom_callable_pass(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body><div id='x'>ok</div></body></html>")
    # 使用同步的 page.evaluate 检查元素存在
    rule = ValidationRule(type="custom", expected=lambda p: p.evaluate("() => !!document.getElementById('x')"))
    result = await validator.validate(page, rule)
    assert result.success is True


@pytest.mark.asyncio
async def test_validate_custom_callable_fail(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body></body></html>")
    rule = ValidationRule(type="custom", expected=lambda p: p.evaluate("() => !!document.getElementById('x')"))
    result = await validator.validate(page, rule)
    assert result.success is False


@pytest.mark.asyncio
async def test_validate_custom_async_callable(browser_page, validator):
    page = browser_page
    await page.set_content("<html><body><h1>Hi</h1></body></html>")
    async def async_check(p):
        return await p.inner_text("h1") == "Hi"
    rule = ValidationRule(type="custom", expected=async_check)
    result = await validator.validate(page, rule)
    assert result.success is True


@pytest.mark.asyncio
async def test_validate_return_code(browser_page, validator):
    page = browser_page
    rule = ValidationRule(type="return_code", expected=200)
    result = await validator.validate(page, rule)
    assert result.success is True
    assert "not applicable" in result.message


@pytest.mark.asyncio
async def test_validate_unknown_type(browser_page, validator):
    page = browser_page
    rule = ValidationRule(type="custom", expected="nonexistent_func")
    validator.register_custom("nonexistent_func", lambda p: False)
    # 测试未知类型
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ValidationRule(type="unknown_type", expected="x")
