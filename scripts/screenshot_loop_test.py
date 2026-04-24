#!/usr/bin/env python3
"""
Screenshot Analysis -> Fix -> Test Loop
Comprehensive Playwright test for Blueclaw v2.5 frontend.
"""
import asyncio
import sys
import os
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


async def setup_page(page: Page):
    """Navigate and wait for WebSocket connection."""
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    # Wait for WS connection
    for _ in range(20):
        await page.wait_for_timeout(500)
        ws_state = await page.evaluate("""
            () => {
                const ws = window.__WEBSOCKET_INSTANCE__;
                return ws ? ws.readyState : -1;
            }
        """)
        if ws_state == 1:
            break
    await page.wait_for_timeout(1000)


async def set_store_state(page: Page, state_updates: dict):
    """Update Zustand store state directly via window.__BLUECLAW_STORE__."""
    # First, expose the store to window if not already done
    await page.evaluate("""
        () => {
            // Try to find the blueprint store by looking for modules
            const findStore = () => {
                // Check if vite has exposed modules
                const viteModules = window.__vite_module_cache__ || {};
                for (const key in viteModules) {
                    const mod = viteModules[key];
                    if (mod && mod.useBlueprintStore) {
                        return mod.useBlueprintStore;
                    }
                }
                return null;
            };
            
            if (!window.__BLUECLAW_STORE__) {
                // Alternative: the store might already be exposed
                // Let's check common patterns
                const keys = Object.keys(window);
                for (const k of keys) {
                    const val = window[k];
                    if (val && typeof val.getState === 'function') {
                        window.__BLUECLAW_STORE__ = val;
                        break;
                    }
                }
            }
        }
    """)
    
    # Try to use the store
    store_exposed = await page.evaluate("""
        () => window.__BLUECLAW_STORE__ !== undefined
    """)
    
    if not store_exposed:
        print("  [Warning] Could not expose Zustand store")
        return False
    
    for key, value in state_updates.items():
        await page.evaluate(f"""
            () => {{
                const store = window.__BLUECLAW_STORE__;
                if (store && store.getState().{key}) {{
                    store.getState().{key}({value});
                }}
            }}
        """)
    
    return True


async def test_state_1_initial(page: Page):
    """State 1: Initial input screen."""
    print("\n[State 1] Initial input screen...")
    await setup_page(page)
    return await take_screenshot(page, "state01_initial")


async def test_state_2_thinking(page: Page):
    """State 2: Thinking phase with nodes."""
    print("\n[State 2] Thinking phase...")
    await setup_page(page)
    
    # Click input and submit to trigger thinking
    try:
        input_box = page.locator('input[placeholder*="规划"]').first
        await input_box.fill("Plan a weekend trip to Hangzhou")
        await page.wait_for_timeout(300)
        
        start_btn = page.locator('button:has-text("开始")').first
        await start_btn.click()
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  [Warning] Could not submit input: {e}")
    
    return await take_screenshot(page, "state02_thinking")


async def test_state_3_execution(page: Page):
    """State 3: Execution phase with steps."""
    print("\n[State 3] Execution phase...")
    await setup_page(page)
    
    # Try to set execution steps via direct store manipulation
    # This requires the store to be accessible
    try:
        await page.evaluate("""
            () => {
                // Look for any zustand store with setState pattern
                const keys = Object.keys(window);
                for (const k of keys) {
                    const val = window[k];
                    if (val && typeof val === 'object' && val.getState && typeof val.getState === 'function') {
                        const state = val.getState();
                        if (state.phase !== undefined) {
                            window.__FOUND_STORE__ = val;
                            break;
                        }
                    }
                }
                
                const store = window.__FOUND_STORE__;
                if (store) {
                    // Set phase to execution
                    const setState = store.setState || store.getState;
                    if (typeof setState === 'function') {
                        store.setState({ 
                            phase: 'execution',
                            executionSteps: [
                                { id: 'step_1', name: 'Search flights', status: 'running', description: 'Finding flights', dependencies: [] },
                                { id: 'step_2', name: 'Book hotel', status: 'pending', description: 'Booking accommodation', dependencies: ['step_1'] },
                                { id: 'step_3', name: 'Plan itinerary', status: 'pending', description: 'Creating schedule', dependencies: ['step_2'] }
                            ],
                            currentTaskId: 'task_test_001',
                            thinkingNodes: [
                                { id: 'think_1', title: 'Transportation', description: 'How to get there', options: [{id:'opt1',text:'Flight',selected:true}] },
                                { id: 'think_2', title: 'Accommodation', description: 'Where to stay', options: [{id:'opt2',text:'Hotel',selected:true}] }
                            ]
                        });
                    }
                }
            }
        """)
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  [Warning] Could not set execution state: {e}")
    
    return await take_screenshot(page, "state03_execution")


async def test_state_4_execution_frozen(page: Page):
    """State 4: Execution step with frozen state."""
    print("\n[State 4] Execution step frozen...")
    await setup_page(page)
    
    try:
        await page.evaluate("""
            () => {
                const store = window.__FOUND_STORE__;
                if (store) {
                    store.setState({ 
                        phase: 'execution',
                        executionSteps: [
                            { id: 'step_1', name: 'Search flights', status: 'running', description: 'Finding flights', dependencies: [] },
                            { id: 'step_2', name: 'Book hotel', status: 'pending', description: 'Booking accommodation', dependencies: ['step_1'] }
                        ],
                        currentTaskId: 'task_test_001',
                        thinkingNodes: [
                            { id: 'think_1', title: 'Transportation', description: 'How to get there', options: [{id:'opt1',text:'Flight',selected:true}] }
                        ]
                    });
                }
            }
        """)
        await page.wait_for_timeout(1500)
        
        # Now send a freeze message via WebSocket to simulate backend freeze
        await page.evaluate("""
            () => {
                const ws = window.__WEBSOCKET_INSTANCE__;
                if (ws && ws.readyState === 1) {
                    ws.send(JSON.stringify({
                        type: 'adapter.runtime.frozen',
                        payload: {
                            blueprint_id: 'step_1',
                            reason: 'Flight search failed - manual intervention needed'
                        },
                        message_id: 'test_freeze_1'
                    }));
                }
            }
        """)
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  [Warning] Could not simulate freeze: {e}")
    
    return await take_screenshot(page, "state04_frozen")


async def test_state_5_visual_adapter(page: Page):
    """State 5: VisualAdapter with runtime state."""
    print("\n[State 5] VisualAdapter panel...")
    await setup_page(page)
    
    try:
        await page.evaluate("""
            () => {
                const store = window.__FOUND_STORE__;
                if (store) {
                    store.setState({ 
                        phase: 'execution',
                        executionSteps: [
                            { id: 'step_1', name: 'Search flights', status: 'running', description: 'Finding flights', dependencies: [] }
                        ],
                        currentTaskId: 'task_test_001',
                        selectedExecutionStepId: 'step_1',
                        thinkingNodes: []
                    });
                }
            }
        """)
        await page.wait_for_timeout(2000)
        
        # Send runtime state message
        await page.evaluate("""
            () => {
                const ws = window.__WEBSOCKET_INSTANCE__;
                if (ws && ws.readyState === 1) {
                    ws.send(JSON.stringify({
                        type: 'adapter.runtime.state',
                        payload: {
                            blueprint_id: 'step_1',
                            studio_id: 'studio_001',
                            task_id: 'task_test_001',
                            adapter_type: 'web',
                            state: 'running',
                            current_url: 'https://example.com/flights',
                            annotations: [
                                { id: 'ann_1', level: 'info', message: 'Searching for flights to Hangzhou', timestamp: Date.now() }
                            ]
                        },
                        message_id: 'test_runtime_1'
                    }));
                }
            }
        """)
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  [Warning] Could not simulate VisualAdapter state: {e}")
    
    return await take_screenshot(page, "state05_visual_adapter")


async def run_all_tests():
    print("=" * 60)
    print("Blueclaw v2.5 Screenshot Loop Test")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        
        # Collect console logs
        all_logs = []
        
        page = await context.new_page()
        page.on("console", lambda msg: all_logs.append((msg.type, msg.text)))
        page.on("pageerror", lambda err: all_logs.append(("pageerror", str(err))))
        
        screenshots = []
        
        try:
            screenshots.append(await test_state_1_initial(page))
            screenshots.append(await test_state_2_thinking(page))
            screenshots.append(await test_state_3_execution(page))
            screenshots.append(await test_state_4_execution_frozen(page))
            screenshots.append(await test_state_5_visual_adapter(page))
        except Exception as e:
            print(f"\n[ERROR] Test suite failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
        
        # Report
        print("\n" + "=" * 60)
        print("SCREENSHOT REPORT")
        print("=" * 60)
        print(f"Screenshots saved to: {SCREENSHOT_DIR}")
        for s in screenshots:
            size = s.stat().st_size
            print(f"  - {s.name} ({size/1024:.1f} KB)")
        
        # Console errors
        errors = [log for log in all_logs if log[0] in ('error', 'pageerror')]
        if errors:
            print(f"\nConsole errors ({len(errors)}):")
            for t, text in errors[:20]:
                print(f"  [{t}] {text}")
        else:
            print("\nNo console errors detected.")
        
        return screenshots, errors


if __name__ == "__main__":
    screenshots, errors = asyncio.run(run_all_tests())
    sys.exit(1 if errors else 0)
