#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 04: Data Scraping

Demonstrates extracting structured data from a page:
1. Navigate to a product list page
2. Scroll to load more items
3. Extract data via Playwright evaluate
4. Print scraped results

Run: python examples/web/04_scrape.py
"""
import asyncio
import os
import tempfile
import json

from playwright.async_api import async_playwright

from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot

HTML = """<!DOCTYPE html>
<html>
<head><title>Products</title></head>
<body>
  <h1>Product List</h1>
  <div class="product" data-name="Apple" data-price="1.2"></div>
  <div class="product" data-name="Banana" data-price="0.8"></div>
  <div class="product" data-name="Cherry" data-price="2.5"></div>
</body>
</html>
"""


async def main():
    tmpdir = tempfile.mkdtemp()
    html_path = os.path.join(tmpdir, "products.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML)
    url = f"file:///{html_path.replace(os.sep, '/')}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        executor = WebExecutor(screenshot_capture=PlaywrightScreenshot())

        steps = [
            ExecutionStep(
                step_id="nav",
                name="Open product page",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic=url)),
            ),
            ExecutionStep(
                step_id="scroll",
                name="Scroll down",
                action=ActionDefinition(type="scroll", params={"dx": 0, "dy": 300}),
            ),
        ]

        for step in steps:
            print(f"[RUN] {step.name} ... ", end="", flush=True)
            result = await executor.execute_step(step, page, blueprint_id="ex04")
            print("OK" if result.status == "success" else f"FAIL ({result.error or result.output})")

        # Extract data directly via Playwright
        print("[EXTRACT] Scraping product data ... ", end="", flush=True)
        products = await page.evaluate("""() => {
            const nodes = document.querySelectorAll('.product');
            return Array.from(nodes).map(n => ({
                name: n.getAttribute('data-name'),
                price: parseFloat(n.getAttribute('data-price'))
            }));
        }""")
        print("OK")
        print("[RESULT] Scraped products:")
        print(json.dumps(products, indent=2, ensure_ascii=False))

        await browser.close()

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 04 complete.")


if __name__ == "__main__":
    asyncio.run(main())
