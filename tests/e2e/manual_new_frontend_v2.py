#!/usr/bin/env python3
"""
Complete manual interaction test for new frontend
Correct click strategy: click on node header area to expand
"""
import asyncio
from playwright.async_api import async_playwright
import os

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = "blueclawv2/blueclawv2/screenshots/new_frontend_v2"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def click_node_header(page, node_locator):
    """Click on the top header area of a thinking node to expand it."""
    bbox = await node_locator.bounding_box()
    if not bbox:
        return False
    # Click on the white header area (top 60px of node)
    x = bbox['x'] + bbox['width'] / 2
    y = bbox['y'] + 40
    await page.mouse.click(x, y)
    return True

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        logs = []
        page.on("console", lambda msg: logs.append((msg.type, msg.text)))
        
        # ====== Step 0: Initial page ======
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/00_initial.png")
        print("[00] Initial page loaded")
        
        # ====== Step 1: Input ======
        input_box = page.locator('input').first
        await input_box.fill("我想规划一个周末短途旅行")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_input.png")
        print("[01] Input filled")
        
        # Submit
        await page.locator('button:has-text("开始")').first.click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_after_submit.png")
        print("[02] After submit")
        
        # ====== Step 2: Click first thinking node to expand ======
        node1 = page.locator('.react-flow__node-thinking').first
        await click_node_header(page, node1)
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_node1_expanded.png")
        print("[03] Node 1 expanded")
        
        # ====== Step 3: Select option A ======
        option_a = page.locator('button:has-text("A. 自然风光")').first
        if await option_a.count() > 0:
            await option_a.click()
            print("[04] Option A selected")
        else:
            # Fallback: click first option button
            opt = page.locator('.react-flow__node-thinking >> button').nth(2)
            if await opt.count() > 0:
                await opt.click()
                print("[04] First option selected (fallback)")
        
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/04_after_option1.png")
        
        # ====== Step 4: Click second thinking node ======
        nodes = page.locator('.react-flow__node-thinking')
        count = await nodes.count()
        print(f"[05] Thinking nodes: {count}")
        
        if count >= 2:
            node2 = nodes.nth(1)
            await click_node_header(page, node2)
            await page.wait_for_timeout(800)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/05_node2_expanded.png")
            print("[05] Node 2 expanded")
            
            # Select option on node 2
            option_a2 = page.locator('button:has-text("A.")').first
            if await option_a2.count() > 0:
                await option_a2.click()
                print("[06] Node 2 Option A selected")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/06_after_option2.png")
        
        # ====== Step 5: Third node ======
        count = await page.locator('.react-flow__node-thinking').count()
        print(f"[07] Thinking nodes after 2nd selection: {count}")
        
        if count >= 3:
            node3 = page.locator('.react-flow__node-thinking').nth(2)
            await click_node_header(page, node3)
            await page.wait_for_timeout(800)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/07_node3_expanded.png")
            print("[07] Node 3 expanded")
            
            # Auto-select should happen on 3rd round in mock mode
            # But let's manually select if needed
            option_a3 = page.locator('button:has-text("A.")').first
            if await option_a3.count() > 0:
                await option_a3.click()
                print("[08] Node 3 Option A selected")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/08_after_option3.png")
        
        # ====== Step 6: Execution phase ======
        await page.wait_for_timeout(3000)
        exec_nodes = await page.locator('.react-flow__node-execution').count()
        summary_nodes = await page.locator('.react-flow__node-summary').count()
        print(f"[09] Execution nodes: {exec_nodes}, Summary nodes: {summary_nodes}")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/09_execution.png")
        
        # Wait for execution to progress
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/10_execution_progress.png")
        print("[10] Execution progress captured")
        
        # ====== Console logs ======
        print("\n--- Console logs ---")
        for level, text in logs[-20:]:
            print(f"  [{level}] {text[:200]}")
        
        await browser.close()

asyncio.run(main())
