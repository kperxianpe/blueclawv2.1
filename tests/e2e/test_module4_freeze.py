#!/usr/bin/env python3
"""
Module 4: Freeze Annotation (FR-001~003)
"""
import pytest
from playwright.async_api import Page
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_framework import Framework, Status

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "module4"


async def _inject_thinking_state(page):
    """Inject minimal thinking state so canvas is not empty."""
    await page.evaluate("""
        () => {
            if (window.__BLUECLAW_SET__) {
                window.__BLUECLAW_SET__({
                    phase: 'thinking',
                    thinkingNodes: [
                        {
                            id: 'freeze_demo_t1',
                            question: 'T1: Freeze Target Selection',
                            status: 'pending',
                            allowCustom: true,
                            options: [
                                {id: 'A', label: 'Web Page', description: 'Freeze and annotate a web page', confidence: 0.9, isDefault: true},
                                {id: 'B', label: 'IDE Code', description: 'Freeze and annotate code location', confidence: 0.7}
                            ]
                        }
                    ],
                    currentThinkingIndex: 0,
                    selectedThinkingNodeId: 'freeze_demo_t1'
                });
                return true;
            }
            return false;
        }
    """)
    await page.wait_for_timeout(800)
    # Trigger fitView if available
    await page.evaluate("""
        () => { if (window.__REACTFLOW_FITVIEW__) window.__REACTFLOW_FITVIEW__(); }
    """)
    await page.wait_for_timeout(600)


@pytest.mark.asyncio
async def test_fr001_active_freeze(page: Page):
    """FR-001: Active Freeze - Web Page Annotation"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("FR-001", "Module 4: Freeze Annotation",
                   "Active Freeze - Web Page Annotation",
                   "User clicks freeze button, interface dims, supports area selection and text annotation")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Inject thinking state so freeze_button screenshot shows canvas, not empty page
    await _inject_thinking_state(page)
    
    # Try to find freeze button
    freeze_btn = page.locator('button').filter(has_text='Freeze').first
    has_freeze = await freeze_btn.is_visible(timeout=2000)
    
    if not has_freeze:
        await fw.checkpoint("freeze_button", "Freeze Button Check",
                           status=Status.GAP,
                           notes="Freeze button not found, freeze function UI completely missing")
    
    fw.mark_gap(
        "Freeze annotation system completely unimplemented: 1) No freeze button 2) No freeze mode overlay 3) No selection tool 4) No annotation input box 5) No re-execute/replan options",
        "1. Create FreezeButton component 2. Implement FreezeOverlay fullscreen mask 3. Add RegionSelector selection component 4. Create AnnotationInput popup 5. Implement freeze state management"
    )


@pytest.mark.asyncio
async def test_fr002_auto_freeze(page: Page):
    """FR-002: Auto Freeze - Element Not Found"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("FR-002", "Module 4: Freeze Annotation",
                   "Auto Freeze - Element Not Found",
                   "AI operation failure auto-triggers freeze, displays error prompt and page screenshot")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    await _inject_thinking_state(page)
    
    await fw.checkpoint("auto_freeze", "Auto Freeze Trigger Check",
                       status=Status.GAP,
                       notes="No auto freeze trigger mechanism, only red node shown on error")
    
    fw.mark_gap(
        "Auto freeze not implemented: 1) No auto freeze when element not found 2) No error prompt popup 3) No page screenshot display 4) No element library update mechanism",
        "1. Add auto freeze trigger in WebExecutor error handling 2. Create ErrorPrompt component 3. Implement page screenshot capture 4. Add element selector learning mechanism"
    )


@pytest.mark.asyncio
async def test_fr003_ide_freeze(page: Page):
    """FR-003: IDE Freeze - Code Location Annotation"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("FR-003", "Module 4: Freeze Annotation",
                   "IDE Freeze - Code Location Annotation",
                   "IDE interface screenshot, select correct location, rollback error operations on re-execute")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    await _inject_thinking_state(page)
    
    await fw.checkpoint("ide_freeze", "IDE Freeze Check",
                       status=Status.GAP,
                       notes="No IDE view, no freeze annotation function")
    
    fw.mark_gap(
        "IDE freeze not implemented: 1) No IDE view 2) No code screenshot 3) No line number mapping 4) No rollback mechanism",
        "1. First implement IDE Adapter base 2. Add code screenshot feature 3. Implement selection to line number mapping 4. Add code rollback and re-insert logic"
    )
