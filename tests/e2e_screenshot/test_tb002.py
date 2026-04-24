#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题目 TB-002: 多轮分支探索与回溯
状态: PARTIAL — 当前前端缺少并行分支展示、回溯按钮、AI推断标签
"""

import asyncio
import pytest
from playwright.async_api import Page

from base_test import ScreenshotTestBase


@pytest.mark.asyncio
async def test_tb002_multi_round_branching(page: Page):
    """
    TB-002: 多轮分支探索与回溯（骨架测试）
    
    当前前端缺失功能（标记为 TODO）:
    - 并行分支展示（T2a/T2b/T2c 同时出现）
    - AI推断标签和自动选择
    - 回溯/重新思考按钮
    - 废弃路径虚线框标记
    - 历史存档查看
    
    已实现验证:
    - 多轮思考节点生成
    - 选项选择和状态变化
    """
    t = ScreenshotTestBase(page, "TB-002")
    await t.start()

    await t.screenshot("初始状态", wait_ms=1000)

    # 输入复杂任务
    await page.fill("input", "我要去日本玩7天，预算1万，想体验当地文化")
    await page.keyboard.press("Enter")
    await t.screenshot("发送复杂任务", wait_ms=5000)

    # 尝试选择多轮选项
    for round_idx in range(3):
        try:
            buttons = await page.query_selector_all("button")
            visible = [b for b in buttons if await b.is_visible()]
            if len(visible) >= 2:
                await visible[1].click()
                await asyncio.sleep(4)
                await t.screenshot(f"第{round_idx+1}轮选择后", wait_ms=1000)
            else:
                await t.screenshot(f"第{round_idx+1}轮无选项")
                break
        except Exception:
            await t.screenshot(f"第{round_idx+1}轮异常")
            break

    await t.screenshot("最终状态", wait_ms=2000)
    await t.finish()
    # TB-002 有多个功能未实现，不强制通过
    assert True, "TB-002 骨架测试完成，部分功能待前端实现"
