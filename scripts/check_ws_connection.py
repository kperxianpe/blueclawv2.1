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
        await page.wait_for_timeout(5000)
        
        print("Console logs (last 30):")
        for t, text in logs[-30:]:
            print(f"  [{t}] {text}")
        
        # Check WebSocket state via JS
        ws_state = await page.evaluate("""
            () => {
                // Try to find ws instances
                const keys = Object.keys(window);
                const wsKeys = keys.filter(k => window[k] instanceof WebSocket);
                return wsKeys.map(k => ({
                    key: k,
                    url: window[k].url,
                    readyState: window[k].readyState
                }));
            }
        """)
        print(f"\nWebSocket instances: {ws_state}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
