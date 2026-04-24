#!/usr/bin/env python3
"""
Module 2: Execution Blueprint (EB-001~003)
"""
import pytest
from playwright.async_api import Page
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_framework import Framework, Status

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "module2"


@pytest.mark.asyncio
async def test_eb001_basic_execution(page: Page):
    """EB-001: Basic Execution Flow - Information Retrieval Task"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("EB-001", "Module 2: Execution Blueprint",
                   "Basic Execution Flow - Information Retrieval",
                   "Generate execution blueprint, execute step by step, support expanding to view detailed logs")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Set execution state directly via store
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'step_1', name: 'Search Dianping', status: 'completed', description: 'Search Shanghai cafes', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true, result: 'Found 15 cafes' },
                        { id: 'step_2', name: 'Search Xiaohongshu', status: 'running', description: 'Search Xiaohongshu recommendations', dependencies: ['step_1'], position: { x: 300, y: 100 }, isMainPath: true },
                        { id: 'step_3', name: 'Cross Validation', status: 'pending', description: 'Merge and compare data', dependencies: ['step_2'], position: { x: 500, y: 100 }, isMainPath: true },
                        { id: 'step_4', name: 'Generate Ranking', status: 'pending', description: 'Top 5 list', dependencies: ['step_3'], position: { x: 700, y: 100 }, isMainPath: true },
                        { id: 'step_5', name: 'Output Report', status: 'pending', description: 'Generate final document', dependencies: ['step_4'], position: { x: 900, y: 100 }, isMainPath: true },
                    ],
                    selectedExecutionStepId: 'step_2'
                });
            }
        }
    """)
    await page.wait_for_timeout(2000)
    
    await fw.checkpoint("execution_started", "Execution Blueprint Generated", notes="Check 5 step nodes")
    
    # Check for step states
    has_execution = await page.evaluate("""
        () => {
            const store = window.__BLUECLAW_STORE__;
            return store && store.executionSteps && store.executionSteps.length >= 5;
        }
    """)
    
    if not has_execution:
        fw.mark_fail("Execution steps not properly set")
        return
    
    # Click on running node to expand
    node = page.locator('.react-flow__node-execution').nth(1)
    if await node.is_visible(timeout=3000):
        await node.click()
        await page.wait_for_timeout(1000)
        await fw.checkpoint("node_expanded", "Execution Node Expanded", notes="Check progress bar and log area")
    
    # Check for pulse animation on running node
    await fw.checkpoint("running_animation", "Running Animation", notes="Check pulse animation effect")
    
    fw.mark_pass()


@pytest.mark.asyncio
async def test_eb002_parallel_execution(page: Page):
    """EB-002: Parallel Execution - Multi-channel Data Collection"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("EB-002", "Module 2: Execution Blueprint",
                   "Parallel Execution - Multi-channel Data Collection",
                   "Parallel branches execute simultaneously, independent progress bars, convergence node")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Set parallel execution state
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'step_1', name: 'Search Products', status: 'completed', description: 'iPhone 15', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                        { id: 'step_2a', name: 'JD Price', status: 'completed', description: '5999 CNY', dependencies: ['step_1'], position: { x: 300, y: 50 }, isMainPath: false },
                        { id: 'step_2b', name: 'Taobao Price', status: 'completed', description: '5899 CNY', dependencies: ['step_1'], position: { x: 300, y: 150 }, isMainPath: false },
                        { id: 'step_2c', name: 'Pinduoduo Price', status: 'running', description: 'Querying...', dependencies: ['step_1'], position: { x: 300, y: 250 }, isMainPath: false },
                        { id: 'step_3', name: 'Price Comparison', status: 'pending', description: 'Three-platform comparison', dependencies: ['step_2a', 'step_2b', 'step_2c'], position: { x: 500, y: 150 }, isMainPath: true, isConvergence: true },
                    ],
                    selectedExecutionStepId: 'step_2c'
                });
            }
        }
    """)
    await page.wait_for_timeout(2000)
    
    await fw.checkpoint("parallel_started", "Parallel Execution Started", notes="Check branch structure")
    
    # Check for parallel branch visualization
    # Gap: Frontend doesn't show independent progress bars per branch
    await fw.checkpoint("progress_bars", "Independent Progress Bars Check",
                       status=Status.GAP,
                       notes="Frontend independent progress bar per branch not implemented")
    
    # Check for convergence node
    nodes = page.locator('.react-flow__node-execution')
    count = await nodes.count()
    if count >= 4:
        await fw.checkpoint("convergence_node", "Convergence Node", notes=f"Total {count} execution nodes")
    
    fw.mark_gap(
        "Parallel execution visualization incomplete: 1) Independent progress bars missing 2) Branch grouping markers missing 3) Waiting state for completed branches missing",
        "1. Add branch progress bar group to ExecutionNode 2. Add parallel grouping visual markers 3. Implement waiting state style"
    )


@pytest.mark.asyncio
async def test_eb003_self_healing(page: Page):
    """EB-003: Failure and Self-healing - Web Scraping Failure"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("EB-003", "Module 2: Execution Blueprint",
                   "Failure and Self-healing - Web Scraping Failure",
                   "Step turns red on failure, auto-trigger self-healing, display healing records")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Set failed state with needsIntervention
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'step_1', name: 'Prepare Request', status: 'completed', description: 'Set headers', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                        { id: 'step_2', name: 'Parse Page', status: 'completed', description: 'Parse DOM', dependencies: ['step_1'], position: { x: 300, y: 100 }, isMainPath: true },
                        { id: 'step_3', name: 'Scrape Zhihu Hot List', status: 'failed', description: 'Element selector failed', dependencies: ['step_2'], position: { x: 500, y: 100 }, isMainPath: true, needsIntervention: true, error: 'Element selector failed (404)' },
                        { id: 'step_4', name: 'Aggregate Data', status: 'pending', description: 'Merge hot list data', dependencies: ['step_3'], position: { x: 700, y: 100 }, isMainPath: true },
                    ],
                    selectedExecutionStepId: 'step_3'
                });
            }
        }
    """)
    await page.wait_for_timeout(2000)
    
    await fw.checkpoint("failed_state", "Failed State Display", notes="Check red error node")
    
    # Click failed node to see error details
    node = page.locator('.react-flow__node-execution').nth(2)
    if await node.is_visible(timeout=3000):
        await node.click()
        await page.wait_for_timeout(1000)
        await fw.checkpoint("error_details", "Error Details Expanded", notes="Check error info and retry count")
    
    # Gap: Self-healing UI doesn't exist
    await fw.checkpoint("self_healing", "Self-healing Process Check",
                       status=Status.GAP,
                       notes="Frontend auto self-healing UI not implemented: no 'Trying self-healing...' prompt, no healing markers")
    
    # Gap: Orange healing state doesn't exist
    await fw.checkpoint("healing_state", "Self-healing State Color",
                       status=Status.GAP,
                       notes="Status types only have pending/running/completed/failed, no healing/orange status")
    
    fw.mark_gap(
        "Failure self-healing not implemented: 1) Auto self-healing trigger logic missing 2) Self-healing status (orange) UI missing 3) Self-healing log records missing 4) Alternative attempt visualization missing",
        "1. Add SelfHealingProvider component 2. Extend ExecutionStep type with 'healing' status 3. Implement self-healing log panel 4. Add alternative switching animation"
    )
