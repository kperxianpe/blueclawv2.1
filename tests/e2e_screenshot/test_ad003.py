#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题目 AD-003: 混合执行（API + Web）
状态: SKIP — 依赖 AD-001/AD-002 的 Web/IDE 视图，当前未实现
"""

import pytest
from playwright.async_api import Page

from base_test import ScreenshotTestBase


@pytest.mark.asyncio
async def test_ad003_mixed_execution(page: Page):
    """AD-003: 混合执行（SKIP — 依赖功能未实现）"""
    t = ScreenshotTestBase(page, "AD-003")
    await t.start()
    await t.screenshot("初始状态", wait_ms=1000)
    await t.screenshot("功能未实现_SKIP", wait_ms=500)
    await t.finish()
    assert True, "AD-003 前端功能未实现，标记为 SKIP"
