#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 05: Distraction Handling + Recovery

Demonstrates:
1. A page with an advertisement popup
2. DistractionDetector marks the popup
3. WebLocator finds the real target behind distractions
4. Fallback selector recovery if primary selector fails

Run: python examples/web/05_distraction_recovery.py
"""
import asyncio
import os
import tempfile

from playwright.async_api import async_playwright

from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.web.recovery import RecoveryController, RecoveryConfig
from blueclaw.adapter.web.checkpoint import WebCheckpointManager
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.web.visualization import CanvasMindVisualizer

HTML = """<!DOCTYPE html>
<html>
<head><title>Ad Demo</title>
<style>
  #ad-popup { position:fixed; top:20px; left:20px; width:200px; height:100px;
              background:#ff0; z-index:9999; padding:10px; }
  #real-btn { margin-top:150px; }
</style>
</head>
<body>
  <div id="ad-popup">AD: Buy Now! <button onclick="this.parentElement.remove()">Close</button></div>
  <h1>Main Content</h1>
  <button id="real-btn" onclick="document.getElementById('msg').textContent='Success!'">Real Button</button>
  <div id="msg"></div>
</body>
</html>
"""


async def main():
    tmpdir = tempfile.mkdtemp()
    html_path = os.path.join(tmpdir, "ad_demo.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML)
    url = f"file:///{html_path.replace(os.sep, '/')}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        cp_mgr = WebCheckpointManager(base_dir=os.path.join(tmpdir, "cp"))
        recovery = RecoveryController(
            web_checkpoint_manager=cp_mgr,
            config=RecoveryConfig(
                max_retries=1,
                fallback_selectors=["#real-btn"],
                enable_rollback=False,
            ),
        )
        executor = WebExecutor(
            screenshot_capture=PlaywrightScreenshot(),
            recovery_controller=recovery,
            visualizer=CanvasMindVisualizer(),
            web_checkpoint_manager=cp_mgr,
        )

        steps = [
            ExecutionStep(
                step_id="nav",
                name="Open page with ad",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic=url)),
            ),
            ExecutionStep(
                step_id="wait",
                name="Wait for popup",
                action=ActionDefinition(type="wait", params={"ms": 500}),
            ),
            ExecutionStep(
                step_id="click_real",
                name="Click real button (ad present)",
                action=ActionDefinition(
                    type="click",
                    target=TargetDescription(semantic="Real Button"),
                ),
            ),
        ]

        for step in steps:
            print(f"[RUN] {step.name} ... ", end="", flush=True)
            result = await executor.execute_step(step, page, blueprint_id="ex05")
            if result.status == "success" and "Recovered" in result.output:
                print(f"OK (recovered: {result.output})")
            else:
                print("OK" if result.status == "success" else f"FAIL ({result.error or result.output})")

        final = await page.locator("#msg").inner_text()
        print(f"[VERIFY] Final message: '{final}'")

        await browser.close()

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 05 complete.")


if __name__ == "__main__":
    asyncio.run(main())
