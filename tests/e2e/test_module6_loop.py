#!/usr/bin/env python3
"""
Module 6: Loop Protection (LP-001~003)
"""
import pytest
import json
from playwright.async_api import Page
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_framework import Framework, Status

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "module6"


async def _inject_loop_execution_state(page, iterations=5, current=4, status_prefix="completed"):
    """Inject execution steps that look like a loop."""
    steps = []
    for i in range(1, iterations + 1):
        st = "completed" if i < current else ("running" if i == current else "pending")
        steps.append({
            "id": f'loop_{i}',
            "name": 'Scrape Page',
            "status": st,
            "description": f'Page {i}/{iterations}',
            "dependencies": [f'loop_{i-1}'] if i > 1 else [],
            "position": {"x": 100 + (i-1) * 200, "y": 100},
            "isMainPath": True
        })
    steps_json = json.dumps(steps)
    await page.evaluate(f"""
        () => {{
            if (window.__BLUECLAW_SET__) {{
                window.__BLUECLAW_SET__({{
                    phase: 'execution',
                    executionSteps: {steps_json},
                    selectedExecutionStepId: 'loop_{current}'
                }});
                return true;
            }}
            return false;
        }}
    """)
    await page.wait_for_timeout(800)
    await page.evaluate("""
        () => { if (window.__REACTFLOW_FITVIEW__) window.__REACTFLOW_FITVIEW__(); }
    """)
    await page.wait_for_timeout(600)


@pytest.mark.asyncio
async def test_lp001_normal_loop(page: Page):
    """LP-001: Normal Loop - Page-turning Scrape"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("LP-001", "Module 6: Loop Protection",
                   "Normal Loop - Page-turning Scrape",
                   "Loop executes 5 times without triggering protection, display page number and count")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Set loop execution state
    await page.evaluate("""
        () => {
            const set = window.__BLUECLAW_SET__;
            if (set) {
                set({
                    phase: 'execution',
                    executionSteps: [
                        { id: 'loop_1', name: 'Scrape Page', status: 'completed', description: 'Page 1/5', dependencies: [], position: { x: 100, y: 100 }, isMainPath: true },
                        { id: 'loop_2', name: 'Scrape Page', status: 'completed', description: 'Page 2/5', dependencies: ['loop_1'], position: { x: 300, y: 100 }, isMainPath: true },
                        { id: 'loop_3', name: 'Scrape Page', status: 'completed', description: 'Page 3/5', dependencies: ['loop_2'], position: { x: 500, y: 100 }, isMainPath: true },
                        { id: 'loop_4', name: 'Scrape Page', status: 'running', description: 'Page 4/5', dependencies: ['loop_3'], position: { x: 700, y: 100 }, isMainPath: true },
                        { id: 'loop_5', name: 'Scrape Page', status: 'pending', description: 'Page 5/5', dependencies: ['loop_4'], position: { x: 900, y: 100 }, isMainPath: true },
                    ],
                    selectedExecutionStepId: 'loop_4'
                });
            }
        }
    """)
    await page.wait_for_timeout(800)
    await page.evaluate("""
        () => { if (window.__REACTFLOW_FITVIEW__) window.__REACTFLOW_FITVIEW__(); }
    """)
    await page.wait_for_timeout(600)
    
    await fw.checkpoint("loop_execution", "Loop Execution", notes="Check 5 loop steps")
    
    # Check for loop counter visualization
    # Gap: No loop counter badge on nodes
    await fw.checkpoint("loop_counter", "Loop Counter Check",
                       status=Status.GAP,
                       notes="Execution nodes have no loop count display (1/10), no page number labels")
    
    fw.mark_gap(
        "Loop visualization not implemented: 1) Execution nodes have no loop counter 2) No page/iteration labels 3) 'Loop completed' status",
        "1. Add LoopCounter badge to ExecutionNode 2. Add PageNumber/Iteration labels 3. Create LoopCompleted state style"
    )


@pytest.mark.asyncio
async def test_lp002_loop_overflow(page: Page):
    """LP-002: Loop Overflow - Infinite Scroll Trap"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("LP-002", "Module 6: Loop Protection",
                   "Loop Overflow - Infinite Scroll Trap",
                   "Loop 10 times triggers protection, auto-pause, prompt user choice")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Inject execution state with many loop iterations before gap checkpoint
    await _inject_loop_execution_state(page, iterations=10, current=8)
    
    await fw.checkpoint("overflow_protection", "Overflow Protection Check",
                       status=Status.GAP,
                       notes="No loop counter, no overflow auto-pause mechanism, no user intervention options")
    
    fw.mark_gap(
        "Loop protection not implemented: 1) No max_iterations config 2) No loop counter (8 times yellow warning, 10 times red pause) 3) No auto-pause logic 4) No user intervention options (continue/stop/freeze)",
        "1. Add LoopConfig to execution step class 2. Implement LoopCounter component (with color warnings) 3. Add loop check in ExecutionEngine 4. Create LoopInterventionPanel"
    )


@pytest.mark.asyncio
async def test_lp003_polling_timeout(page: Page):
    """LP-003: Loop Exception - Polling Detection Timeout"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("LP-003", "Module 6: Loop Protection",
                   "Loop Exception - Polling Detection Timeout",
                   "Poll every 30 seconds interval, auto-pause after timeout, display diagnostic info")
    
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    
    await fw.checkpoint("initial", "Initial Interface")
    
    # Inject execution state with polling-like steps before gap checkpoint
    await _inject_loop_execution_state(page, iterations=6, current=5)
    
    await fw.checkpoint("polling_timeout", "Polling Timeout Check",
                       status=Status.GAP,
                       notes="No polling interval config, no timeout diagnostics, no last state display")
    
    fw.mark_gap(
        "Polling timeout protection not implemented: 1) No polling interval config (30s) 2) No timeout auto-pause 3) No diagnostic info (last few states) 4) No user intervention options",
        "1. Add PollingConfig to step config 2. Implement polling timer and timeout check 3. Create PollingDiagnostics component 4. Add user intervention options"
    )
