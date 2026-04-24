#!/usr/bin/env python3
"""
Module 5: Intervention (IV-001~003)
"""
import pytest
from playwright.async_api import Page
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_framework import Framework, Status

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "module5"


@pytest.mark.asyncio
async def test_iv001_retry(page: Page):
    """IV-001: Re-execute - Step Retry"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("IV-001", "Module 5: Intervention",
                   "Re-execute - Step Retry",
                   "Failed steps show retry count, user can manually trigger retry")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Set failed state
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'step_1', name: 'Prepare', status: 'completed', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                        { id: 'step_2', name: 'Scrape', status: 'completed', dependencies: ['step_1'], position: { x: 300, y: 100 }, isMainPath: true },
                        { id: 'step_3', name: 'Parse', status: 'failed', description: 'Network Timeout', dependencies: ['step_2'], position: { x: 500, y: 100 }, isMainPath: true, needsIntervention: true, error: 'Timeout after 30s' },
                    ],
                    selectedExecutionStepId: 'step_3'
                });
            }
        }
    """)
    await page.wait_for_timeout(2000)
    
    await fw.checkpoint("failed_state", "Failed State", notes="Check red error node")
    
    # Click node to expand
    node = page.locator('.react-flow__node-execution').nth(2)
    if await node.is_visible(timeout=3000):
        await node.click()
        await page.wait_for_timeout(1000)
        await fw.checkpoint("node_expanded", "Node Expanded", notes="Check intervention buttons")
    
    # Check for retry button
    retry_btn = page.locator('button').filter(has_text='Retry').first
    has_retry = await retry_btn.is_visible(timeout=2000)
    
    if not has_retry:
        await fw.checkpoint("retry_button", "Retry Button Check",
                           status=Status.GAP,
                           notes="InterventionPanel missing Retry option, only Continue/Replan/Stop")
    
    fw.mark_gap(
        "Retry intervention incomplete: 1) InterventionPanel missing Retry button 2) No retry count display (1/2) 3) No confirmation popup 4) No auto-retry 3 times then fail logic",
        "1. Add Retry option to InterventionPanel 2. Show retry count on ExecutionNode 3. Add confirmation popup component 4. Implement auto-retry logic"
    )


@pytest.mark.asyncio
async def test_iv002_replan(page: Page):
    """IV-002: Replan - Strategy Adjustment"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("IV-002", "Module 5: Intervention",
                   "Replan - Strategy Adjustment",
                   "Preserve completed steps, regenerate thinking nodes and execution blueprint from breakpoint")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Set partial execution state
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'step_1', name: 'Search', status: 'completed', result: '15 items', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                        { id: 'step_2', name: 'Filter', status: 'completed', result: '8 items', dependencies: ['step_1'], position: { x: 300, y: 100 }, isMainPath: true },
                        { id: 'step_3', name: 'Analyze', status: 'completed', result: '3 items', dependencies: ['step_2'], position: { x: 500, y: 100 }, isMainPath: true },
                        { id: 'step_4', name: 'Generate Report', status: 'running', description: 'Strategy Issue', dependencies: ['step_3'], position: { x: 700, y: 100 }, isMainPath: true },
                    ],
                    selectedExecutionStepId: 'step_4'
                });
            }
        }
    """)
    await page.wait_for_timeout(2000)
    
    await fw.checkpoint("partial_execution", "Partial Execution State", notes="Steps 1-3 completed, step 4 running")
    
    # Trigger intervention panel
    node = page.locator('.react-flow__node-execution').nth(3)
    if await node.is_visible(timeout=3000):
        # Look for replan button on node
        replan_btn = node.locator('button').filter(has_text='Replan')
        has_replan = await replan_btn.is_visible(timeout=2000)
        if has_replan:
            await replan_btn.click()
            await page.wait_for_timeout(1000)
            await fw.checkpoint("intervention_panel", "Intervention Panel", notes="Check replan options")
    
    # Check for new branch generation in mock mode
    await fw.checkpoint("new_branch", "New Branch Generation Check",
                       status=Status.GAP,
                       notes="Mock mode replan only injects fixed branch steps, not real rethink")
    
    fw.mark_gap(
        "Replan incomplete: 1) Mock mode replan is fixed logic, not real AI rethink 2) No old/new blueprint comparison 3) No archived steps storage 4) No thinking blueprint re-entry",
        "1. Connect backend thinking.restart_thinking_from_intervention 2. Create BlueprintDiff comparison component 3. Add ArchivedStepsPanel 4. Implement thinking blueprint re-activation"
    )


@pytest.mark.asyncio
async def test_iv003_combo_intervention(page: Page):
    """IV-003: Combo Intervention - Freeze + Replan"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("IV-003", "Module 5: Intervention",
                   "Combo Intervention - Freeze + Replan",
                   "Freeze annotation combined with replan, annotation content as Replan input context")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    await fw.checkpoint("combo_flow", "Combo Intervention Flow Check",
                       status=Status.GAP,
                       notes="Freeze and replan functions both incomplete, cannot be combined")
    
    fw.mark_gap(
        "Combo intervention not implemented: 1) Freeze function missing 2) Data flow between freeze and Replan not established 3) No mechanism to pass annotation content to Replan",
        "1. First implement basic freeze function 2. Attach annotation context to Replan request 3. Implement annotation to thinking node conversion"
    )
