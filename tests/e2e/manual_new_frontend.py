#!/usr/bin/env python3
"""
Manual interaction test for new frontend (buleclawv1-frontword)
Simulates real user: input -> click expand -> select option -> observe
"""
import asyncio
from playwright.async_api import async_playwright

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = "blueclawv2/screenshots/new_frontend_manual"

import os
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        logs = []
        page.on("console", lambda msg: logs.append((msg.type, msg.text)))
        
        # Step 0: Open page
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/00_initial_page.png")
        print("[00] Initial page loaded")
        
        # Step 1: Input text
        input_box = page.locator('input[placeholder*="输入"] , textarea[placeholder*="输入"], input[type="text"]').first
        if await input_box.count() == 0:
            # Try broader selectors
            input_box = page.locator('input').first
        
        if await input_box.count() > 0:
            await input_box.fill("我想规划一个周末短途旅行")
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/01_input_filled.png")
            print("[01] Input filled")
            
            # Submit - try clicking submit button or pressing Enter
            submit_btn = page.locator('button[type="submit"], button:has-text("提交"), button:has-text("开始"), button:has-text("发送")').first
            if await submit_btn.count() > 0:
                await submit_btn.click()
            else:
                await input_box.press("Enter")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/02_after_submit.png")
            print("[02] After submit")
        else:
            print("[01] WARNING: No input box found")
            await page.screenshot(path=f"{SCREENSHOT_DIR}/01_no_input.png")
        
        # Step 2: Check for thinking nodes
        thinking_nodes = page.locator('.react-flow__node-thinking')
        count = await thinking_nodes.count()
        print(f"[03] Thinking nodes visible: {count}")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_thinking_nodes.png")
        
        if count > 0:
            # Step 3: Click first thinking node to expand
            first_node = thinking_nodes.first
            bbox = await first_node.bounding_box()
            print(f"[04] First node bbox: {bbox}")
            
            if bbox:
                # Click on the node to expand
                await first_node.click()
                await page.wait_for_timeout(800)
                await page.screenshot(path=f"{SCREENSHOT_DIR}/04_node_clicked.png")
                print("[04] First node clicked")
                
                # Step 4: Check if options are visible after click
                options = page.locator('button:has-text("A."), button:has-text("B."), [class*="option"], .bg-gray-800')
                opt_count = await options.count()
                print(f"[05] Options visible: {opt_count}")
                await page.screenshot(path=f"{SCREENSHOT_DIR}/05_options_visible.png")
                
                # Step 5: Click an option if visible
                if opt_count > 0:
                    first_option = options.first
                    await first_option.click()
                    await page.wait_for_timeout(1500)
                    await page.screenshot(path=f"{SCREENSHOT_DIR}/06_option_selected.png")
                    print("[06] Option selected")
                    
                    # Wait for next node
                    await page.wait_for_timeout(2000)
                    count2 = await page.locator('.react-flow__node-thinking').count()
                    print(f"[07] Thinking nodes after selection: {count2}")
                    await page.screenshot(path=f"{SCREENSHOT_DIR}/07_after_selection.png")
                    
                    # Click second node
                    if count2 > 1:
                        second_node = page.locator('.react-flow__node-thinking').nth(1)
                        await second_node.click()
                        await page.wait_for_timeout(800)
                        await page.screenshot(path=f"{SCREENSHOT_DIR}/08_second_node_clicked.png")
                        print("[08] Second node clicked")
                        
                        # Select option on second node
                        options2 = page.locator('button:has-text("A."), button:has-text("B.")')
                        if await options2.count() > 0:
                            await options2.first.click()
                            await page.wait_for_timeout(1500)
                            await page.screenshot(path=f"{SCREENSHOT_DIR}/09_second_option_selected.png")
                            print("[09] Second option selected")
                            
                            # Wait for thinking complete -> execution
                            await page.wait_for_timeout(3000)
                            await page.screenshot(path=f"{SCREENSHOT_DIR}/10_execution_phase.png")
                            print("[10] Execution phase")
                            
                            # Check execution nodes
                            exec_count = await page.locator('.react-flow__node-execution').count()
                            print(f"[11] Execution nodes: {exec_count}")
                            await page.screenshot(path=f"{SCREENSHOT_DIR}/11_execution_nodes.png")
        
        print("\n--- Console logs ---")
        for level, text in logs[-30:]:
            print(f"  [{level}] {text[:200]}")
        
        await browser.close()

asyncio.run(main())
