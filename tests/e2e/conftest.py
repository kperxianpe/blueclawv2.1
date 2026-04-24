#!/usr/bin/env python3
"""
Pytest fixtures for Blueclaw v2.5 E2E screenshot testing.
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import pytest
import pytest_asyncio

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
BASELINE_DIR = PROJECT_ROOT / "tests" / "e2e" / "baselines"


@pytest_asyncio.fixture
async def browser():
    """Launch Playwright browser once per test session."""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser):
    """Create a new browser page with WS monitoring."""
    from playwright.async_api import Page
    
    context = await browser.new_context(viewport={"width": 1600, "height": 1000})
    
    ws_messages: List[Dict[str, Any]] = []
    console_logs: List[tuple] = []
    
    def on_ws_frame(frame: str):
        try:
            data = json.loads(frame)
            ws_messages.append(data)
        except Exception:
            pass
    
    pg = await context.new_page()
    pg.on("console", lambda msg: console_logs.append((msg.type, msg.text)))
    pg.on("pageerror", lambda err: console_logs.append(("pageerror", str(err))))
    pg.on("websocket", lambda ws: ws.on("framereceived", on_ws_frame))
    
    # Attach metadata for tests
    pg._ws_messages = ws_messages
    pg._console_logs = console_logs
    
    yield pg
    
    await context.close()


@pytest.fixture
def ws_messages(page):
    """Access WebSocket messages captured during the test."""
    return page._ws_messages


@pytest.fixture
def console_logs(page):
    """Access console logs captured during the test."""
    return page._console_logs
