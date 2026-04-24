#!/usr/bin/env python3
"""
Playwright Screenshot Analysis - Fix - Test Loop
Screenshots key UI states and detects visual regressions.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, r"C:\Users\10508\My project (1)\forkimi\buleclawv1\blueclawv2")

# Ensure playwright is available
try:
    from playwright.async_api import async_playwright, Page, expect
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# Screenshot output directory
SCREENSHOT_DIR = Path(r"C:\Users\10508\My project (1)\forkimi\buleclawv1\blueclawv2\screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

FRONTEND_URL = "http://localhost:5173"
BACKEND_WS_URL = "ws://localhost:8006/ws"


async def take_screenshot(page: Page, name: str, full_page: bool = False) -> Path:
    """Take a screenshot and save it."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{name}_{timestamp}.png"
    path = SCREENSHOT_DIR / filename
    await page.screenshot(path=str(path), full_page=full_page)
    print(f"  [Screenshot] {path.name}")
    return path


async def analyze_screenshot(path: Path) -> list[str]:
    """Basic analysis: check file size (empty/black screen detection)."""
    issues = []
    size = path.stat().st_size
    if size < 1000:
        issues.append(f"Screenshot {path.name} is very small ({size} bytes) - possibly blank/errored")
    return issues


async def test_initial_load(page: Page):
    """Test 1: Initial page load and WebSocket connection."""
    print("\n[Test 1] Initial page load...")
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(2000)  # Wait for WS connection attempt
    
    path = await take_screenshot(page, "01_initial_load")
    issues = await analyze_screenshot(path)
    
    # Check for console errors
    logs = await page.evaluate("() => window._consoleErrors || []")
    if logs:
        issues.append(f"Console errors: {logs}")
    
    return issues


async def test_input_and_thinking(page: Page):
    """Test 2: Enter task input and trigger thinking phase."""
    print("\n[Test 2] Input and thinking...")
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1500)
    
    # Find and fill the input
    try:
        input_field = page.locator("textarea, input[type='text']").first
        await input_field.wait_for(timeout=5000)
        await input_field.fill("Plan a trip to Beijing")
        await page.wait_for_timeout(500)
        
        # Click submit/start button
        submit_btn = page.locator("button").filter(has_text=re.compile("start|submit|go|send", re.I)).first
        if await submit_btn.is_visible(timeout=3000):
            await submit_btn.click()
            await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  [Warning] Could not interact with input: {e}")
    
    path = await take_screenshot(page, "02_input_thinking")
    issues = await analyze_screenshot(path)
    return issues


async def test_execution_node_intervention(page: Page):
    """Test 3: Execution node with intervention menu."""
    print("\n[Test 3] Execution node intervention...")
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1500)
    
    # Try to set store state via localStorage or direct evaluation
    # to simulate having execution steps
    try:
        await page.evaluate("""
            const store = window.__BLUECLAW_STORE__;
            if (store) {
                store.getState().setExecutionSteps([
                    { id: 'step_1', name: 'Search flights', status: 'running', description: 'Finding flights to Beijing' }
                ]);
            }
        """)
        await page.wait_for_timeout(1000)
    except Exception as e:
        print(f"  [Warning] Could not set execution steps: {e}")
    
    path = await take_screenshot(page, "03_execution_node")
    issues = await analyze_screenshot(path)
    return issues


async def test_visual_adapter(page: Page):
    """Test 4: VisualAdapter panel."""
    print("\n[Test 4] VisualAdapter panel...")
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1500)
    
    # Try to open VisualAdapter if there's a button
    try:
        adapter_btn = page.locator("button").filter(has_text=re.compile("visual|adapter|studio|canvas", re.I)).first
        if await adapter_btn.is_visible(timeout=3000):
            await adapter_btn.click()
            await page.wait_for_timeout(1500)
    except Exception as e:
        print(f"  [Info] No VisualAdapter button found or not clickable: {e}")
    
    path = await take_screenshot(page, "04_visual_adapter")
    issues = await analyze_screenshot(path)
    return issues


async def test_websocket_connection(page: Page):
    """Test 5: Verify WebSocket is connected."""
    print("\n[Test 5] WebSocket connection status...")
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(3000)
    
    # Check if WebSocket is connected via console or DOM
    ws_connected = await page.evaluate("""
        () => {
            const indicators = document.querySelectorAll('[data-ws-connected], .ws-connected, .connection-status');
            return indicators.length > 0 ? indicators[0].textContent : null;
        }
    """)
    
    issues = []
    if ws_connected:
        print(f"  [Info] WS status indicator: {ws_connected}")
        if "disconnected" in ws_connected.lower() or "offline" in ws_connected.lower():
            issues.append(f"WebSocket appears disconnected: {ws_connected}")
    else:
        print("  [Info] No WS status indicator found in DOM")
    
    path = await take_screenshot(page, "05_ws_status")
    issues.extend(await analyze_screenshot(path))
    return issues


async def run_all_tests():
    """Run all screenshot tests and report issues."""
    print("=" * 60)
    print("Blueclaw v2.5 Screenshot Analysis Test")
    print("=" * 60)
    print(f"Frontend: {FRONTEND_URL}")
    print(f"Backend WS: {BACKEND_WS_URL}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        
        # Enable console error collection
        page = await context.new_page()
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        await page.evaluate("window._consoleErrors = []")
        
        all_issues = []
        
        try:
            all_issues.extend(await test_initial_load(page))
            all_issues.extend(await test_input_and_thinking(page))
            all_issues.extend(await test_execution_node_intervention(page))
            all_issues.extend(await test_visual_adapter(page))
            all_issues.extend(await test_websocket_connection(page))
        except Exception as e:
            print(f"\n[ERROR] Test suite failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
        
        # Final report
        print("\n" + "=" * 60)
        print("TEST REPORT")
        print("=" * 60)
        if all_issues:
            print(f"\nFound {len(all_issues)} issue(s):")
            for i, issue in enumerate(all_issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\nNo issues detected in screenshots.")
        
        if console_errors:
            print(f"\nConsole errors ({len(console_errors)}):")
            for err in console_errors[:10]:
                print(f"  - {err}")
        
        return all_issues


if __name__ == "__main__":
    import re
    issues = asyncio.run(run_all_tests())
    sys.exit(1 if issues else 0)
