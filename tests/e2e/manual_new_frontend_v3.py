#!/usr/bin/env python3
"""
Test with precise option selection for node 3
"""
import asyncio
from playwright.async_api import async_playwright
import os

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = "blueclawv2/blueclawv2/screenshots/new_frontend_v3"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def click_node_header(page, node_locator):
    bbox = await node_locator.bounding_box()
    if not bbox:
        return False
    x = bbox['x'] + bbox['width'] / 2
    y = bbox['y'] + 40
    await page.mouse.click(x, y)
    return True

async def select_first_option_in_node(page, node_index):
    """Select the first option button inside a specific thinking node."""
    node = page.locator('.react-flow__node-thinking').nth(node_index)
    # Find option buttons inside this node (exclude '重新思考' and '其他...')
    option_buttons = node.locator('button').filter(has_text=r'^[A-D]\.')
    count = await option_buttons.count()
    if count > 0:
        await option_buttons.first.click()
        return True
    # Fallback: click any button that looks like an option
    all_btns = node.locator('button')
    for i in range(await all_btns.count()):
        btn = all_btns.nth(i)
        text = await btn.inner_text()
        if text and len(text) > 0 and '重新思考' not in text and '其他' not in text and '确认' not in text:
            await btn.click()
            return True
    return False

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        logs = []
        page.on("console", lambda msg: logs.append((msg.type, msg.text)))
        
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/00_initial.png")
        print("[00] Initial page loaded")
        
        # Input
        await page.locator('input').first.fill("我想规划一个周末短途旅行")
        await page.locator('button:has-text(\"开始\")').first.click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_after_submit.png")
        print("[01] After submit")
        
        # Node 1: expand -> select option A
        node1 = page.locator('.react-flow__node-thinking').first
        await click_node_header(page, node1)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_node1_expanded.png")
        print("[02] Node 1 expanded")
        
        await select_first_option_in_node(page, 0)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_after_node1_select.png")
        print("[03] Node 1 option selected")
        
        # Node 2: expand -> select option A
        count = await page.locator('.react-flow__node-thinking').count()
        print(f"[04] Thinking nodes: {count}")
        
        if count >= 2:
            node2 = page.locator('.react-flow__node-thinking').nth(1)
            await click_node_header(page, node2)
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/04_node2_expanded.png")
            print("[04] Node 2 expanded")
            
            await select_first_option_in_node(page, 1)
            await page.wait_for_timeout(1500)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/05_after_node2_select.png")
            print("[05] Node 2 option selected")
        
        # Node 3: expand -> select option A (this should trigger completeThinking)
        count = await page.locator('.react-flow__node-thinking').count()
        print(f"[06] Thinking nodes after node2: {count}")
        
        if count >= 3:
            node3 = page.locator('.react-flow__node-thinking').nth(2)
            await click_node_header(page, node3)
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/06_node3_expanded.png")
            print("[06] Node 3 expanded")
            
            success = await select_first_option_in_node(page, 2)
            if success:
                print("[07] Node 3 option selected")
            else:
                print("[07] FAILED to select node 3 option")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/07_after_node3_select.png")
        
        # Check execution phase
        await page.wait_for_timeout(3000)
        phase = await page.evaluate("""() => {
            const store = window.__BLUECLAW_STORE__;
            return store ? store.phase : 'unknown';
        }""")
        exec_count = await page.locator('.react-flow__node-execution').count()
        summary_count = await page.locator('.react-flow__node-summary').count()
        print(f"[08] Phase: {phase}, Execution nodes: {exec_count}, Summary: {summary_count}")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/08_execution.png")
        
        # Wait for execution progress
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/09_execution_progress.png")
        print("[09] Execution progress captured")
        
        print("\n--- Console logs ---")
        for level, text in logs[-20:]:
            print(f"  [{level}] {text[:200]}")
        
        await browser.close()

asyncio.run(main())
