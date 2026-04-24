#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 07: Custom Validation Rule

Demonstrates writing a custom validation function:
1. Navigate to a page with dynamic content
2. Use a custom async validator to check element count
3. Print validation result

Run: python examples/web/07_custom_validation.py
"""
import asyncio
import os
import tempfile

from playwright.async_api import async_playwright

from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription, ValidationRule
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.web.validator import WebValidator
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot

HTML = """<!DOCTYPE html>
<html>
<head><title>Dynamic</title></head>
<body>
  <div id="list">
    <div class="item">A</div>
    <div class="item">B</div>
    <div class="item">C</div>
  </div>
</body>
</html>
"""


async def custom_check(page) -> bool:
    """Custom validator: require at least 3 items."""
    count = await page.locator(".item").count()
    return count >= 3


async def main():
    tmpdir = tempfile.mkdtemp()
    html_path = os.path.join(tmpdir, "list.html")
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
                step_id="nav",
                name="Open list page",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic=url)),
            ),
            ExecutionStep(
                step_id="validate",
                name="Validate item count >= 3",
                action=ActionDefinition(type="wait", params={"ms": 200}),
                validation=ValidationRule(
                    type="custom",
                    expected=custom_check,
                ),
            ),
        ]

        for step in steps:
            print(f"[RUN] {step.name} ... ", end="", flush=True)
            result = await executor.execute_step(step, page, blueprint_id="ex07")
            print("OK" if result.status == "success" else f"FAIL ({result.error or result.output})")

        await browser.close()

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 07 complete.")


if __name__ == "__main__":
    asyncio.run(main())
