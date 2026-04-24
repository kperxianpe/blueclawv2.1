#!/usr/bin/env python3
"""
Test with force click and scroll to handle off-screen nodes
"""
import asyncio
from playwright.async_api import async_playwright
import os

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = "blueclawv2/blueclawv2/screenshots/new_frontend_v4"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def click_node_header(page, node_locator):
    bbox = await node_locator.bounding_box()
    if not bbox:
        return False
    x = bbox['x'] + bbox['width'] / 2
    y = bbox['y'] + 40
    await page.mouse.click(x, y)
    return True

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/00_initial.png")
        
        # Input and submit
        await page.locator('input').first.fill("我想规划一个周末短途旅行")
        await page.locator('button:has-text(\"开始\")').first.click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_after_submit.png")
        
        # Node 1: expand -> select
        node1 = page.locator('.react-flow__node-thinking').first
        await click_node_header(page, node1)
        await page.wait_for_timeout(600)
        
        # Get all buttons in node 1, click the one with option A
        btns = page.locator('.react-flow__node-thinking').first.locator('button')
        for i in range(await btns.count()):
            text = await btns.nth(i).inner_text()
            if 'A.' in text or '自然风光' in text:
                await btns.nth(i).click()
                print(f"[02] Node 1 option clicked: {text[:30]}")
                break
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_after_n1.png")
        
        # Node 2: expand -> select
        node2 = page.locator('.react-flow__node-thinking').nth(1)
        await click_node_header(page, node2)
        await page.wait_for_timeout(600)
        
        btns2 = page.locator('.react-flow__node-thinking').nth(1).locator('button')
        for i in range(await btns2.count()):
            text = await btns2.nth(i).inner_text()
            if 'A.' in text or '杭州' in text:
                await btns2.nth(i).click()
                print(f"[03] Node 2 option clicked: {text[:30]}")
                break
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_after_n2.png")
        
        # Node 3: expand -> select (use force click if off-screen)
        count = await page.locator('.react-flow__node-thinking').count()
        print(f"[04] Total thinking nodes: {count}")
        
        if count >= 3:
            node3 = page.locator('.react-flow__node-thinking').nth(2)
            
            # Try to scroll node into view using JS
            await page.evaluate("""(selector) => {
                const el = document.querySelector(selector);
                if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
            }""", await node3.evaluate("el => '.' + Array.from(el.classList).join('.')"))
            await page.wait_for_timeout(300)
            
            await click_node_header(page, node3)
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/04_n3_expanded.png")
            
            # Find option buttons in node 3 using force click
            btns3 = page.locator('.react-flow__node-thinking').nth(2).locator('button')
            clicked = False
            for i in range(await btns3.count()):
                text = await btns3.nth(i).inner_text()
                if 'A.' in text or '本周末' in text:
                    await btns3.nth(i).click(force=True)
                    print(f"[05] Node 3 option clicked: {text[:30]}")
                    clicked = True
                    break
            
            if not clicked:
                # Fallback: click first button that isn't 重新思考
                for i in range(await btns3.count()):
                    text = await btns3.nth(i).inner_text()
                    if '重新思考' not in text and len(text.strip()) > 0:
                        await btns3.nth(i).click(force=True)
                        print(f"[05] Node 3 fallback clicked: {text[:30]}")
                        clicked = True
                        break
            
            await page.wait_for_timeout(3000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/05_after_n3.png")
        
        # Check phase via DOM
        phase_text = await page.locator('text=思考中').count()
        exec_nodes = await page.locator('.react-flow__node-execution').count()
        print(f"[06] Phase 'thinking' indicators: {phase_text}, Execution nodes: {exec_nodes}")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/06_execution.png")
        
        await browser.close()

asyncio.run(main())
