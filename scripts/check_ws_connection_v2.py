#!/usr/bin/env python3
"""Check if frontend WebSocket connects to backend correctly."""
import asyncio
import sys

sys.path.insert(0, r"C:\Users\10508\My project (1)\forkimi\buleclawv1\blueclawv2")

from playwright.async_api import async_playwright

FRONTEND_URL = "http://localhost:5173"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        logs = []
        page.on("console", lambda msg: logs.append((msg.type, msg.text)))
        page.on("pageerror", lambda err: logs.append(("pageerror", str(err))))
        
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        
        # Wait up to 10 seconds for WS connection
        for i in range(20):
            await page.wait_for_timeout(500)
            ws_state = await page.evaluate("""
                () => {
                    const ws = window.__WEBSOCKET_INSTANCE__;
                    return ws ? { url: ws.url, readyState: ws.readyState } : null;
                }
            """)
            if ws_state and ws_state.get("readyState") == 1:
                print(f"WebSocket CONNECTED after {(i+1)*0.5}s")
                print(f"  URL: {ws_state['url']}")
                break
            print(f"  Waiting for WS... {(i+1)*0.5}s")
        else:
            print("WebSocket NOT connected after 10s")
        
        # Check store connection state
        store_state = await page.evaluate("""
            () => {
                const store = window.__BLUECLAW_STORE__;
                if (store) return store.getState();
                // Try to find zustand store
                const keys = Object.keys(window).filter(k => k.toLowerCase().includes('store'));
                return { storeKeys: keys };
            }
        """)
        print(f"\nStore state: {store_state}")
        
        print("\nConsole logs (last 30):")
        for t, text in logs[-30:]:
            print(f"  [{t}] {text}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
