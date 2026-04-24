#!/usr/bin/env python3
"""
Module 3: Adapter Visualization (AD-001~003)
"""
import pytest
from playwright.async_api import Page
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_framework import Framework, Status

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "module3"


@pytest.mark.asyncio
async def test_ad001_web_adapter(page: Page):
    """AD-001: Web Adapter - Auto Search and Form Filling"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("AD-001", "Module 3: Adapter Visualization",
                   "Web Adapter - Auto Search and Form Filling",
                   "VisualAdapter auto-switches to Web view, displays browser operation process")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface - VisualAdapter displays canvas tab")
    
    # Set execution state to trigger adapter
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'step_1', name: 'Navigate to Douban', status: 'running', description: 'douban.com', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                    ],
                    selectedExecutionStepId: 'step_1'
                });
            }
        }
    """)
    await page.wait_for_timeout(2000)
    
    await fw.checkpoint("adapter_visible", "VisualAdapter Visible", notes="Check bottom panel")
    
    # Check for Web tab
    web_tab = page.locator('[role="tab"]').filter(has_text='Web').first
    has_web_tab = await web_tab.is_visible(timeout=2000)
    
    if not has_web_tab:
        await fw.checkpoint("web_tab", "Web Tab Check",
                           status=Status.GAP,
                           notes="VisualAdapter not showing Web tab, only tool drag interface")
    else:
        await web_tab.click()
        await page.wait_for_timeout(1000)
        await fw.checkpoint("web_view", "Web View", notes="Check WebBrowser component")
    
    fw.mark_gap(
        "Web Adapter not implemented: 1) VisualAdapter only shows tool drag, not real Web browsing 2) No auto-switch view logic 3) No browser operation visualization (click ripple, input animation)",
        "1. Create WebBrowser component connecting to backend WebExecutor 2. Implement view auto-switch logic 3. Add operation animation effects (click ripple, input highlight)"
    )


@pytest.mark.asyncio
async def test_ad002_ide_adapter(page: Page):
    """AD-002: IDE Adapter - Code Generation and Validation"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("AD-002", "Module 3: Adapter Visualization",
                   "IDE Adapter - Code Generation and Validation",
                   "VisualAdapter switches to IDE view, displays VSCode mock interface and code generation")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'step_1', name: 'Generate React Component', status: 'running', description: 'Login.tsx', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                    ],
                    selectedExecutionStepId: 'step_1'
                });
            }
        }
    """)
    await page.wait_for_timeout(2000)
    
    await fw.checkpoint("adapter_visible", "VisualAdapter Visible")
    
    ide_tab = page.locator('[role="tab"]').filter(has_text='IDE').first
    has_ide_tab = await ide_tab.is_visible(timeout=2000)
    
    if not has_ide_tab:
        await fw.checkpoint("ide_tab", "IDE Tab Check",
                           status=Status.GAP,
                           notes="No IDE tab, current VisualAdapter only has tool canvas")
    
    fw.mark_gap(
        "IDE Adapter not implemented: 1) No IDE tab 2) No file tree, editor, terminal panels 3) No code typewriter effect 4) No syntax validation terminal output",
        "1. Create IDEPanel component (file tree + editor + terminal three-column layout) 2. Connect backend IDE API 3. Implement code line-by-line generation animation 4. Add terminal color output"
    )


@pytest.mark.asyncio
async def test_ad003_mixed_execution(page: Page):
    """AD-003: Mixed Execution - API + Web Combo Task"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("AD-003", "Module 3: Adapter Visualization",
                   "Mixed Execution - API + Web Combo",
                   "API steps complete on canvas, Web steps auto-switch view")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Check view switching capability
    await fw.checkpoint("view_switch", "View Switch Check",
                       status=Status.GAP,
                       notes="No canvas/Web/IDE view switching mechanism, VisualAdapter only has single tool canvas")
    
    fw.mark_gap(
        "Mixed execution view switching not implemented: 1) No multi-view tab switching 2) No auto-switch logic 3) No view switch transition animation 4) API results cannot pass to Web steps",
        "1. Refactor VisualAdapter to multi-tab view 2. Implement step type to view auto-mapping 3. Add view switch transition animation 4. Implement inter-step data passing"
    )
