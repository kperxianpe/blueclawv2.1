#!/usr/bin/env python3
"""Debug: Why thinking node doesn't expand on click"""
import asyncio
from playwright.async_api import async_playwright

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = "blueclawv2/blueclawv2/screenshots/debug_click"

import os
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        
        # Submit input
        input_box = page.locator('input').first
        await input_box.fill("我想规划一个周末短途旅行")
        await page.locator('button:has-text("开始")').first.click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_thinking_node.png")
        
        # Get node element handle
        node = page.locator('.react-flow__node-thinking').first
        bbox = await node.bounding_box()
        print(f"Node bbox: {bbox}")
        
        # Method 1: Click the top expand area (the white header)
        # The node has a white top bar with the question text
        # Let's click directly on the text/question area
        if bbox:
            # Click on the center-top of the node (where the header is)
            header_y = bbox['y'] + 30  # top header area
            header_x = bbox['x'] + bbox['width'] / 2
            print(f"Clicking header at: ({header_x}, {header_y})")
            await page.mouse.click(header_x, header_y)
            await page.wait_for_timeout(1000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/02_click_header.png")
            
            # Check if expanded content exists
            expanded = await page.locator('.react-flow__node-thinking >> .bg-gray-900').count()
            print(f"Expanded content elements: {expanded}")
            
            # Method 2: Click the ChevronDown icon specifically
            chevron = page.locator('.react-flow__node-thinking').locator('[class*="ChevronDown"]').first
            if await chevron.count() > 0:
                print("Found ChevronDown, clicking it")
                await chevron.click()
                await page.wait_for_timeout(1000)
                await page.screenshot(path=f"{SCREENSHOT_DIR}/03_click_chevron.png")
            else:
                print("No ChevronDown found")
            
            # Method 3: Use force click on the node
            await node.click(force=True)
            await page.wait_for_timeout(1000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/04_force_click.png")
            
            # Method 4: Double click
            await node.dblclick()
            await page.wait_for_timeout(1000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/05_dblclick.png")
            
            # Check DOM for expanded state
            html = await page.content()
            has_expanded = 'bg-gray-900' in html and '选择方案' in html
            print(f"DOM contains expanded content: {has_expanded}")
            
            # Check for options in DOM
            options_in_dom = await page.locator('text=A.').count()
            print(f"Options 'A.' in DOM: {options_in_dom}")
        
        await browser.close()

asyncio.run(main())
