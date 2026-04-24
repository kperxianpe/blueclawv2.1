#!/usr/bin/env python3
"""
Screenshot Analysis -> Fix -> Test Loop (v2)
Maintains page state across screenshots for realistic UI progression.
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, r"C:\Users\10508\My project (1)\forkimi\buleclawv1\blueclawv2")

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)

SCREENSHOT_DIR = Path(r"C:\Users\10508\My project (1)\forkimi\buleclawv1\blueclawv2\screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

FRONTEND_URL = "http://localhost:5173"


async def take_screenshot(page: Page, name: str) -> Path:
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{name}_{timestamp}.png"
    path = SCREENSHOT_DIR / filename
    await page.screenshot(path=str(path), full_page=False)
    print(f"  [Screenshot] {path.name}")
    return path


async def wait_for_ws(page: Page):
    for _ in range(20):
        await page.wait_for_timeout(500)
        ws_state = await page.evaluate("""
            () => {
                const ws = window.__WEBSOCKET_INSTANCE__;
                return ws ? ws.readyState : -1;
            }
        """)
        if ws_state == 1:
            return True
    return False


async def expose_store(page: Page):
    """Verify Zustand stores are exposed on window."""
    return await page.evaluate("""
        () => {
            // Stores should already be exposed by the app (dev mode)
            return {
                hasBlueprint: !!window.__BLUECLAW_SET__,
                hasAdapter: !!window.__ADAPTER_SET__
            };
        }
    """)


async def run_tests():
    print("=" * 60)
    print("Blueclaw v2.5 Screenshot Loop Test v2")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        
        all_logs = []
        ws_messages = []
        captured_ws = []
        
        def on_ws_frame(frame):
            try:
                data = json.loads(frame)
                ws_messages.append(data)
            except Exception:
                pass
        
        page = await context.new_page()
        page.on("console", lambda msg: all_logs.append((msg.type, msg.text)))
        page.on("pageerror", lambda err: all_logs.append(("pageerror", str(err))))
        page.on("websocket", lambda ws: (captured_ws.append(ws), ws.on("framereceived", on_ws_frame)))
        
        # === State 1: Initial ===
        print("\n[State 1] Initial input screen...")
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await wait_for_ws(page)
        await page.wait_for_timeout(1000)
        await take_screenshot(page, "state01_initial")
        
        # Verify stores are exposed
        store_info = await expose_store(page)
        print(f"  Store exposed: blueprint={store_info.get('hasBlueprint')}, adapter={store_info.get('hasAdapter')}")
        
        # === State 2: Thinking phase (click through UI) ===
        print("\n[State 2] Thinking phase (UI interaction)...")
        try:
            input_box = page.locator('input[placeholder*="规划"]').first
            await input_box.fill("Plan a weekend trip to Hangzhou")
            await page.wait_for_timeout(300)
            
            start_btn = page.locator('button:has-text("开始")').first
            await start_btn.click()
            await page.wait_for_timeout(4000)
            await take_screenshot(page, "state02_thinking")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state02_thinking_error")
        
        # === State 3: Execution phase (direct store manipulation) ===
        print("\n[State 3] Execution phase...")
        try:
            await page.evaluate("""
                () => {
                    const set = window.__BLUECLAW_SET__;
                    if (set) {
                        set({
                            phase: 'execution',
                            executionSteps: [
                                { id: 'step_1', name: 'Search flights', status: 'running', description: 'Finding flights to Hangzhou', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                                { id: 'step_2', name: 'Book hotel', status: 'pending', description: 'Booking accommodation', dependencies: ['step_1'], position: { x: 300, y: 100 }, isMainPath: true },
                                { id: 'step_3', name: 'Plan itinerary', status: 'pending', description: 'Creating daily schedule', dependencies: ['step_2'], position: { x: 500, y: 100 }, isMainPath: true }
                            ],
                            currentTaskId: 'task_test_001',
                            thinkingNodes: [
                                { id: 'think_1', title: 'Transportation', description: 'How to get there', options: [{id:'opt1',text:'Flight',selected:true}] },
                                { id: 'think_2', title: 'Accommodation', description: 'Where to stay', options: [{id:'opt2',text:'Hotel',selected:true}] }
                            ],
                            selectedExecutionStepId: 'step_1'
                        });
                    }
                }
            """)
            await page.wait_for_timeout(3000)
            await take_screenshot(page, "state03_execution")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state03_execution_error")
        
        # === State 4: Frozen step ===
        print("\n[State 4] Frozen step with annotation...")
        try:
            # Directly update adapter store (simulating WS message processing)
            await page.evaluate("""
                () => {
                    const set = window.__ADAPTER_SET__;
                    if (set) {
                        set((state) => ({
                            ...state,
                            runtimeMap: {
                                ...state.runtimeMap,
                                'step_1': {
                                    ...(state.runtimeMap['step_1'] || {}),
                                    studioId: 'studio_001',
                                    blueprintId: 'step_1',
                                    taskId: 'task_test_001',
                                    adapterType: 'web',
                                    state: 'frozen',
                                    annotations: [
                                        {
                                            id: 'ann_freeze_1',
                                            level: 'freeze',
                                            message: 'Flight search API rate limit exceeded',
                                            timestamp: Date.now(),
                                            stepId: 'step_1'
                                        }
                                    ],
                                    lastUpdated: Date.now()
                                }
                            }
                        }));
                    }
                }
            """)
            await page.wait_for_timeout(2000)
            await take_screenshot(page, "state04_frozen")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state04_frozen_error")
        
        # === State 5: Runtime state with VisualAdapter ===
        print("\n[State 5] VisualAdapter with runtime state...")
        try:
            await page.evaluate("""
                () => {
                    const set = window.__ADAPTER_SET__;
                    if (set) {
                        set((state) => ({
                            ...state,
                            runtimeMap: {
                                ...state.runtimeMap,
                                'step_1': {
                                    ...(state.runtimeMap['step_1'] || {}),
                                    studioId: 'studio_001',
                                    blueprintId: 'step_1',
                                    taskId: 'task_test_001',
                                    adapterType: 'web',
                                    state: 'frozen',
                                    currentUrl: 'https://flights.example.com/search',
                                    annotations: [
                                        { id: 'ann_1', level: 'info', message: 'Searching flights to Hangzhou...', timestamp: Date.now(), stepId: 'step_1' },
                                        { id: 'ann_2', level: 'error', message: 'API rate limit: 429 Too Many Requests', timestamp: Date.now(), stepId: 'step_1' }
                                    ],
                                    lastUpdated: Date.now()
                                }
                            }
                        }));
                    }
                }
            """)
            await page.wait_for_timeout(2000)
            await take_screenshot(page, "state05_visual_adapter")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state05_visual_adapter_error")
        
        # === State 6: Click on execution node to show intervention menu ===
        print("\n[State 6] Execution node with intervention menu...")
        try:
            # Click on the first execution node to expand it
            node = page.locator('.react-flow__node-execution').first
            if await node.is_visible(timeout=3000):
                await node.click()
                await page.wait_for_timeout(1000)
            
            await take_screenshot(page, "state06_intervention")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state06_intervention_error")
        
        # === State 7: Unfreeze ===
        print("\n[State 7] Unfreeze via button click...")
        try:
            # First ensure we're frozen
            await page.evaluate("""
                () => {
                    const set = window.__ADAPTER_SET__;
                    if (set) {
                        set((state) => ({
                            ...state,
                            runtimeMap: {
                                ...state.runtimeMap,
                                'step_1': {
                                    ...(state.runtimeMap['step_1'] || {}),
                                    state: 'frozen',
                                    annotations: [
                                        { id: 'ann_f', level: 'freeze', message: 'Frozen for unfreeze test', timestamp: Date.now(), stepId: 'step_1' }
                                    ],
                                    lastUpdated: Date.now()
                                }
                            }
                        }));
                    }
                }
            """)
            await page.wait_for_timeout(1500)
            
            # Click the unfreeze button in the VisualAdapter freeze layer
            unfreeze_btn = page.locator('button').filter(has_text='解除冻结').first
            if await unfreeze_btn.is_visible(timeout=3000):
                await unfreeze_btn.click()
                await page.wait_for_timeout(2000)
            else:
                print("  [Warning] Unfreeze button not found, using store update")
                await page.evaluate("""
                    () => {
                        const set = window.__ADAPTER_SET__;
                        if (set) {
                            set((state) => ({
                                ...state,
                                runtimeMap: {
                                    ...state.runtimeMap,
                                    'step_1': { ...(state.runtimeMap['step_1'] || {}), state: 'running', lastUpdated: Date.now() }
                                }
                            }));
                        }
                    }
                """)
                await page.wait_for_timeout(1500)
            
            await take_screenshot(page, "state07_unfreeze")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state07_unfreeze_error")
        
        # === State 8: Retry action ===
        print("\n[State 8] Retry action...")
        try:
            # Set node to failed state first
            await page.evaluate("""
                () => {
                    const set = window.__ADAPTER_SET__;
                    if (set) {
                        set((state) => ({
                            ...state,
                            runtimeMap: {
                                ...state.runtimeMap,
                                'step_1': {
                                    ...(state.runtimeMap['step_1'] || {}),
                                    state: 'frozen',
                                    annotations: [
                                        { id: 'ann_retry', level: 'freeze', message: 'Retry requested: API timeout', timestamp: Date.now(), stepId: 'step_1' }
                                    ],
                                    lastUpdated: Date.now()
                                }
                            }
                        }));
                    }
                }
            """)
            await page.wait_for_timeout(1500)
            
            # Click retry from intervention menu
            node = page.locator('.react-flow__node-execution').first
            if await node.is_visible(timeout=3000):
                await node.click()
                await page.wait_for_timeout(500)
                retry_btn = page.locator('button').filter(has_text='重试').first
                if await retry_btn.is_visible(timeout=2000):
                    await retry_btn.click()
                    await page.wait_for_timeout(1500)
            
            await take_screenshot(page, "state08_retry")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state08_retry_error")
        
        # === State 9: Replan action ===
        print("\n[State 9] Replan action...")
        try:
            # Add replan annotation
            await page.evaluate("""
                () => {
                    const set = window.__ADAPTER_SET__;
                    if (set) {
                        set((state) => ({
                            ...state,
                            runtimeMap: {
                                ...state.runtimeMap,
                                'step_1': {
                                    ...(state.runtimeMap['step_1'] || {}),
                                    annotations: [
                                        { id: 'ann_replan', level: 'warning', message: 'Replan requested: change route', timestamp: Date.now(), stepId: 'step_1' }
                                    ],
                                    lastUpdated: Date.now()
                                }
                            }
                        }));
                    }
                }
            """)
            await page.wait_for_timeout(1500)
            
            node = page.locator('.react-flow__node-execution').first
            if await node.is_visible(timeout=3000):
                await node.click()
                await page.wait_for_timeout(500)
                replan_btn = page.locator('button').filter(has_text='重新规划').first
                if await replan_btn.is_visible(timeout=2000):
                    await replan_btn.click()
                    await page.wait_for_timeout(1500)
            
            await take_screenshot(page, "state09_replan")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state09_replan_error")
        
        # === State 10: Dismiss annotation ===
        print("\n[State 10] Dismiss annotation...")
        try:
            # Find and click dismiss on the first annotation
            dismiss_btn = page.locator('button[title*="Dismiss"], .annotation-dismiss, [data-testid="dismiss-annotation"]').first
            # Try alternative selectors
            if not await dismiss_btn.is_visible(timeout=1000):
                dismiss_btn = page.locator('button').filter(has_text='✕').first
            if not await dismiss_btn.is_visible(timeout=1000):
                dismiss_btn = page.locator('button').filter(has_text='×').first
            
            if await dismiss_btn.is_visible(timeout=2000):
                await dismiss_btn.click()
                await page.wait_for_timeout(1500)
            else:
                # Fallback: remove annotation via store
                await page.evaluate("""
                    () => {
                        const set = window.__ADAPTER_SET__;
                        if (set) {
                            set((state) => ({
                                ...state,
                                runtimeMap: {
                                    ...state.runtimeMap,
                                    'step_1': { ...(state.runtimeMap['step_1'] || {}), annotations: [], lastUpdated: Date.now() }
                                }
                            }));
                        }
                    }
                """)
                await page.wait_for_timeout(1500)
            
            await take_screenshot(page, "state10_dismiss")
        except Exception as e:
            print(f"  [Warning] {e}")
            await take_screenshot(page, "state10_dismiss_error")
        
        # === State 11: WebSocket roundtrip test ===
        print("\n[State 11] WebSocket roundtrip...")
        try:
            # Helper to send WS message and wait for response via Playwright monitoring
            async def send_ws_and_wait(pg, msg_type, payload, expected_types, timeout_ms=3000):
                before_count = len(ws_messages)
                await pg.evaluate(f"""
                    () => {{
                        const ws = window.__WEBSOCKET_INSTANCE__;
                        if (ws && ws.readyState === 1) {{
                            ws.send(JSON.stringify({{
                                type: '{msg_type}',
                                payload: {json.dumps(payload)},
                                message_id: 'test_' + Math.random().toString(36).slice(2, 8)
                            }}));
                        }}
                    }}
                """)
                # Poll for new messages matching expected types
                for _ in range(timeout_ms // 200):
                    await pg.wait_for_timeout(200)
                    new_messages = ws_messages[before_count:]
                    matches = [m for m in new_messages if m.get('type') in expected_types]
                    if matches:
                        return matches
                return []
            
            # Step 1: Attach blueprint
            print("  [WS] Sending adapter.blueprint.attach...")
            attach_resp = await send_ws_and_wait(
                page, "adapter.blueprint.attach",
                {"task_id": "task_ws_test", "blueprint_id": "bp_ws", "studio_id": "studio_ws", "adapter_type": "web"},
                ("adapter.blueprint.attach_success", "adapter.blueprint.attached"),
                timeout_ms=4000
            )
            print(f"  [WS] Attach: {len(attach_resp)} response(s)")
            
            # Step 2: Start runtime
            print("  [WS] Sending adapter.runtime.start...")
            start_resp = await send_ws_and_wait(
                page, "adapter.runtime.start",
                {"task_id": "task_ws_test", "blueprint_id": "bp_ws"},
                ("adapter.runtime.state",),
                timeout_ms=3000
            )
            print(f"  [WS] Start: {len(start_resp)} response(s), state={start_resp[0].get('payload',{}).get('state') if start_resp else 'none'}")
            
            # Step 3: Freeze
            print("  [WS] Sending adapter.runtime.freeze...")
            freeze_resp = await send_ws_and_wait(
                page, "adapter.runtime.freeze",
                {"task_id": "task_ws_test", "blueprint_id": "bp_ws", "reason": "WS test freeze"},
                ("adapter.runtime.state", "adapter.runtime.frozen"),
                timeout_ms=3000
            )
            print(f"  [WS] Freeze: {len(freeze_resp)} response(s)")
            
            # Step 4: Unfreeze
            print("  [WS] Sending adapter.runtime.unfreeze...")
            unfreeze_resp = await send_ws_and_wait(
                page, "adapter.runtime.unfreeze",
                {"task_id": "task_ws_test", "blueprint_id": "bp_ws"},
                ("adapter.runtime.state", "adapter.runtime.unfrozen"),
                timeout_ms=3000
            )
            print(f"  [WS] Unfreeze: {len(unfreeze_resp)} response(s)")
            
            # Verify store was updated by WS messages (visual confirmation in screenshot)
            await page.wait_for_timeout(1000)
            
            await take_screenshot(page, "state11_ws_roundtrip")
            
            # Summary
            total_responses = len(attach_resp) + len(start_resp) + len(freeze_resp) + len(unfreeze_resp)
            print(f"  [WS] Total responses received: {total_responses}")
            if total_responses < 4:
                print("  [WS Warning] Some responses may have been missed (check backend logs)")
                # Show all captured types for debugging
                all_types = [m.get('type') for m in ws_messages]
                if all_types:
                    print(f"  [WS Debug] All captured types: {all_types}")
        except Exception as e:
            print(f"  [Warning] {e}")
            import traceback
            traceback.print_exc()
            await take_screenshot(page, "state11_ws_roundtrip_error")
        
        await browser.close()
        
        # Report
        print("\n" + "=" * 60)
        print("SCREENSHOT REPORT")
        print("=" * 60)
        
        errors = [log for log in all_logs if log[0] in ('error', 'pageerror')]
        if errors:
            print(f"Console errors ({len(errors)}):")
            for t, text in errors[:15]:
                print(f"  [{t}] {text}")
        else:
            print("No console errors.")
        
        return errors


if __name__ == "__main__":
    errors = asyncio.run(run_tests())
    sys.exit(1 if errors else 0)
