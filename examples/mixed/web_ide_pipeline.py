#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: Mixed Web + IDE Pipeline

Demonstrates a cross-domain workflow:
1. Web: Scrape a code snippet from a page
2. IDE: Analyze the snippet and generate a fix
3. Web: Verify the fix on a documentation page

Run: python examples/mixed/web_ide_pipeline.py
"""
import asyncio
import os
import tempfile

from playwright.async_api import async_playwright

from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.ide.loop import ModificationLoop, LoopConfig
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator

HTML_CODE_PAGE = """<!DOCTYPE html>
<html>
<head><title>Code Snippet</title></head>
<body>
  <pre id="code">def add(a, b):\n    return a + b\n</pre>
</body>
</html>
"""

HTML_DOC_PAGE = """<!DOCTYPE html>
<html>
<head><title>Docs</title></head>
<body>
  <div id="status">Docs loaded</div>
</body>
</html>
"""


async def main():
    tmpdir = tempfile.mkdtemp()

    # Prepare local HTML pages
    code_path = os.path.join(tmpdir, "code.html")
    doc_path = os.path.join(tmpdir, "doc.html")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(HTML_CODE_PAGE)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(HTML_DOC_PAGE)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        executor = WebExecutor(screenshot_capture=PlaywrightScreenshot())

        # Phase 1: Web - scrape code
        print("[PHASE 1] Web scraping ... ")
        step = ExecutionStep(
            step_id="scrape",
            name="Open code page",
            action=ActionDefinition(
                type="navigate",
                target=TargetDescription(semantic=f"file:///{code_path.replace(os.sep, '/')}"),
            ),
        )
        result = await executor.execute_step(step, page, blueprint_id="mixed")
        print("  Navigate OK" if result.status == "success" else f"  Navigate FAIL")

        code_snippet = await page.locator("#code").inner_text()
        print(f"  Scraped code:\n{code_snippet}")

        # Phase 2: IDE - analyze and improve
        print("[PHASE 2] IDE analysis ... ")
        loop = ModificationLoop(
            code_model=MockCodeModelClient(),
            sandbox=SandboxValidator(project_path=tmpdir),
            config=LoopConfig(max_iterations=2, enable_auto_apply=False),
        )
        ide_result = await loop.run(
            task_description="Add type hints to the function",
            file_context={"snippet.py": code_snippet},
        )
        print(f"  IDE loop success: {ide_result.success}, iterations: {ide_result.iterations}")

        # Phase 3: Web - verify on docs page
        print("[PHASE 3] Web verification ... ")
        step2 = ExecutionStep(
            step_id="verify",
            name="Open docs page",
            action=ActionDefinition(
                type="navigate",
                target=TargetDescription(semantic=f"file:///{doc_path.replace(os.sep, '/')}"),
            ),
        )
        result2 = await executor.execute_step(step2, page, blueprint_id="mixed")
        print("  Docs loaded OK" if result2.status == "success" else "  Docs load FAIL")

        await browser.close()

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Mixed pipeline complete.")


if __name__ == "__main__":
    asyncio.run(main())
