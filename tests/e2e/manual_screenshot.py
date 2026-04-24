import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()
        
        logs = []
        ws_msgs = []
        page.on("console", lambda msg: logs.append((msg.type, msg.text)))
        page.on("websocket", lambda ws: ws.on("framereceived", lambda f: ws_msgs.append(f)))
        
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.screenshot(path="screenshots/batch2/manual_01_start.png")
        print("Screenshot 1: start page")
        
        # Use WS directly (same as E2E tests)
        await page.evaluate("""() => {
            const ws = window.__WEBSOCKET_INSTANCE__;
            if (ws && ws.readyState === 1) {
                ws.send(JSON.stringify({
                    type: 'task.start',
                    payload: { user_input: 'Help me plan a trip to Shanghai' },
                    timestamp: Date.now(),
                    message_id: 'manual_' + Math.random().toString(36).slice(2,8)
                }));
            }
        }""")
        print("task.start sent via WS")
        
        for i in range(10):
            await page.wait_for_timeout(3000)
            await page.screenshot(path=f"screenshots/batch2/manual_02_wait_{i+1}.png")
            
            count = await page.locator('.react-flow__node-thinking').count()
            exec_count = await page.locator('.react-flow__node-execution').count()
            print(f"Screenshot {i+2}: t={(i+1)*3}s thinking={count} execution={exec_count}")
            
            # Print WS messages received so far
            if ws_msgs:
                print(f"  WS msgs: {len(ws_msgs)} total")
                for m in ws_msgs[-3:]:
                    try:
                        d = __import__('json').loads(m)
                        print(f"    -> {d['type']}")
                    except:
                        pass
            
            if exec_count > 0:
                print("Execution nodes visible!")
                break
        
        print("\nConsole logs:")
        for level, text in logs[-20:]:
            print(f"  [{level}] {text[:200]}")
        
        await browser.close()

asyncio.run(main())
