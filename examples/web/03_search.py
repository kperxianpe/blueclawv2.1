#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 03: Search Interaction

Demonstrates semantic search on a page:
1. Navigate to a search page
2. Type query into search box
3. Click search button
4. Validate results appear

Run: python examples/web/03_search.py
"""
import asyncio
import os
import tempfile

from playwright.async_api import async_playwright

from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription, ValidationRule
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.web.validator import WebValidator

HTML = """<!DOCTYPE html>
<html>
<head><title>Search</title></head>
<body>
  <h1>Product Search</h1>
  <input id="q" placeholder="Search products...">
  <button id="search" type="button" onclick="doSearch()">Search</button>
  <div id="results"></div>
  <script>
    function doSearch() {
      var q = document.getElementById('q').value;
      var el = document.getElementById('results');
      if (q) {
        el.innerHTML = '<p class="result">Found: ' + q + '</p>';
      }
    }
  </script>
</body>
</html>
"""


async def main():
    tmpdir = tempfile.mkdtemp()
    html_path = os.path.join(tmpdir, "search.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML)
    url = f"file:///{html_path.replace(os.sep, '/')}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        executor = WebExecutor(
            screenshot_capture=PlaywrightScreenshot(),
            validator=WebValidator(),
        )

        steps = [
            ExecutionStep(
                step_id="open",
                name="Open search page",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic=url)),
            ),
            ExecutionStep(
                step_id="query",
                name="Type search query",
                action=ActionDefinition(
                    type="input",
                    target=TargetDescription(semantic="Search products..."),
                    params={"value": "laptop"},
                ),
            ),
            ExecutionStep(
                step_id="click_search",
                name="Click search button",
                action=ActionDefinition(type="click", target=TargetDescription(semantic="Search")),
            ),
            ExecutionStep(
                step_id="wait_results",
                name="Wait for results",
                action=ActionDefinition(type="wait", params={"ms": 500}),
                validation=ValidationRule(
                    type="presence",
                    expected={"selector": ".result"},
                ),
            ),
        ]

        for step in steps:
            print(f"[RUN] {step.name} ... ", end="", flush=True)
            result = await executor.execute_step(step, page, blueprint_id="ex03")
            print("OK" if result.status == "success" else f"FAIL ({result.error or result.output})")

        await browser.close()

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 03 complete.")


if __name__ == "__main__":
    asyncio.run(main())
