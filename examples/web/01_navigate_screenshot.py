#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 01: Navigate and Screenshot

Demonstrates basic Web adapter usage:
1. Navigate to a URL
2. Take a screenshot
3. Validate page title

Run: python examples/web/01_navigate_screenshot.py
"""
import asyncio
import os
import tempfile

from playwright.async_api import async_playwright

from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription, ValidationRule
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.web.validator import WebValidator


async def main():
    screenshot_dir = tempfile.mkdtemp(prefix="blueclaw_demo_")
    print(f"[INFO] Screenshots will be saved to: {screenshot_dir}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        executor = WebExecutor(
            screenshot_capture=PlaywrightScreenshot(),
            validator=WebValidator(),
        )

        steps = [
            ExecutionStep(
                step_id="navigate",
                name="Navigate to example.com",
                action=ActionDefinition(
                    type="navigate",
                    target=TargetDescription(semantic="https://example.com"),
                ),
                validation=ValidationRule(
                    type="url_match",
                    expected=r"example\.com",
                ),
            ),
            ExecutionStep(
                step_id="screenshot",
                name="Take screenshot",
                action=ActionDefinition(type="screenshot"),
            ),
        ]

        for step in steps:
            print(f"[RUN] {step.name} ... ", end="", flush=True)
            result = await executor.execute_step(step, page, blueprint_id="ex01")
            if result.status == "success":
                print("OK")
            else:
                print(f"FAIL ({result.error or result.output})")

            # Save screenshot if present
            if hasattr(result, "screenshot") and result.screenshot:
                path = os.path.join(screenshot_dir, f"{step.step_id}.webp")
                with open(path, "wb") as f:
                    f.write(result.screenshot)
                print(f"[INFO] Saved screenshot: {path}")

        await browser.close()

    print("[DONE] Example 01 complete.")


if __name__ == "__main__":
    asyncio.run(main())
