#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 02: Form Fill and Submit

Demonstrates form interaction:
1. Navigate to a local HTML form
2. Fill username and password
3. Click submit
4. Validate success message

Run: python examples/web/02_form_fill.py
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
<head><title>Login</title></head>
<body>
  <h1>Login Page</h1>
  <form>
    <input id="user" placeholder="Username">
    <input id="pass" type="password" placeholder="Password">
    <button id="submit" type="button" onclick="document.getElementById('msg').textContent='Login OK'">Login</button>
  </form>
  <div id="msg"></div>
</body>
</html>
"""


async def main():
    tmpdir = tempfile.mkdtemp()
    html_path = os.path.join(tmpdir, "login.html")
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
                name="Open login page",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic=url)),
            ),
            ExecutionStep(
                step_id="fill_user",
                name="Fill username",
                action=ActionDefinition(
                    type="input",
                    target=TargetDescription(semantic="Username"),
                    params={"value": "alice"},
                ),
            ),
            ExecutionStep(
                step_id="fill_pass",
                name="Fill password",
                action=ActionDefinition(
                    type="input",
                    target=TargetDescription(semantic="Password"),
                    params={"value": "secret123"},
                ),
            ),
            ExecutionStep(
                step_id="submit",
                name="Click login",
                action=ActionDefinition(type="click", target=TargetDescription(selector="#submit")),
            ),
            ExecutionStep(
                step_id="verify",
                name="Verify success message",
                action=ActionDefinition(type="wait", params={"ms": 300}),
                validation=ValidationRule(
                    type="text_contains",
                    expected={"selector": "#msg", "text": "Login OK"},
                ),
            ),
        ]

        for step in steps:
            print(f"[RUN] {step.name} ... ", end="", flush=True)
            result = await executor.execute_step(step, page, blueprint_id="ex02")
            print("OK" if result.status == "success" else f"FAIL ({result.error or result.output})")

        await browser.close()

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 02 complete.")


if __name__ == "__main__":
    asyncio.run(main())
