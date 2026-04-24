#!/usr/bin/env python3
"""
Batch 2 E2E Tests: Questions 7-14 (LLM-driven)
Real WebSocket flow: task.start -> thinking -> option selection -> execution blueprint
Screenshots follow the checkpoint specification from the test manual.
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
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "batch2"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def start_task_via_ws(page, user_input, ws_messages, timeout_ms=8000):
    """Send task.start via WebSocket and wait for first thinking node."""
    before = len(ws_messages)
    await page.evaluate(f"""() => {{
        const ws = window.__WEBSOCKET_INSTANCE__;
        if (ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{
                type: 'task.start',
                payload: {{user_input: {json.dumps(user_input)}}},
                message_id: 'test_' + Math.random().toString(36).slice(2,8)
            }}));
        }}
    }}""")
    for _ in range(timeout_ms // 300):
        await page.wait_for_timeout(300)
        new_msgs = ws_messages[before:]
        for m in new_msgs:
            if m.get('type') in ('thinking.node_created', 'task.started'):
                return m
    return None


async def select_option_via_ws(page, task_id, node_id, option_id, ws_messages, timeout_ms=8000):
    """Send thinking.select_option and wait for response."""
    before = len(ws_messages)
    await page.evaluate(f"""() => {{
        const ws = window.__WEBSOCKET_INSTANCE__;
        if (ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{
                type: 'thinking.select_option',
                payload: {{
                    task_id: {json.dumps(task_id)},
                    current_node_id: {json.dumps(node_id)},
                    option_id: {json.dumps(option_id)}
                }},
                message_id: 'test_' + Math.random().toString(36).slice(2,8)
            }}));
        }}
    }}""")
    for _ in range(timeout_ms // 300):
        await page.wait_for_timeout(300)
        new_msgs = ws_messages[before:]
        for m in new_msgs:
            if m.get('type') in ('thinking.option_selected', 'thinking.node_created',
                                  'thinking.completed', 'execution.blueprint_loaded'):
                return m
    return None


async def confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=8000):
    """Send thinking.confirm_execution and wait for blueprint."""
    before = len(ws_messages)
    await page.evaluate(f"""() => {{
        const ws = window.__WEBSOCKET_INSTANCE__;
        if (ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{
                type: 'thinking.confirm_execution',
                payload: {{task_id: {json.dumps(task_id)}}},
                message_id: 'test_' + Math.random().toString(36).slice(2,8)
            }}));
        }}
    }}""")
    for _ in range(timeout_ms // 300):
        await page.wait_for_timeout(300)
        new_msgs = ws_messages[before:]
        for m in new_msgs:
            if m.get('type') in ('execution.blueprint_loaded', 'thinking.execution_confirmed'):
                return m
    return None


async def wait_for_thinking_nodes(page, min_count=1, timeout_ms=15000):
    """Wait for thinking nodes to render in DOM and store."""
    for _ in range(timeout_ms // 400):
        await page.wait_for_timeout(400)
        # Check DOM
        dom_count = await page.locator('.react-flow__node-thinking').count()
        # Check store
        store_count = await page.evaluate("""
            () => {
                const store = window.__BLUECLAW_STORE__;
                return store && store.thinkingNodes ? store.thinkingNodes.length : 0;
            }
        """)
        if dom_count >= min_count and store_count >= min_count:
            return dom_count
    # Return last DOM count for diagnostics
    return await page.locator('.react-flow__node-thinking').count()


async def wait_for_execution_steps(page, min_count=1, timeout_ms=15000):
    """Wait for execution steps to render in DOM and store."""
    for _ in range(timeout_ms // 400):
        await page.wait_for_timeout(400)
        dom_count = await page.locator('.react-flow__node-execution').count()
        store_count = await page.evaluate("""
            () => {
                const store = window.__BLUECLAW_STORE__;
                return store && store.executionSteps ? store.executionSteps.length : 0;
            }
        """)
        if dom_count >= min_count and store_count >= min_count:
            return dom_count
    return await page.locator('.react-flow__node-execution').count()


async def fit_reactflow_view(page):
    """Trigger ReactFlow fitView to ensure nodes are in viewport."""
    await page.evaluate("""
        () => {
            if (window.__REACTFLOW_FITVIEW__) {
                window.__REACTFLOW_FITVIEW__();
                return true;
            }
            return false;
        }
    """)
    await page.wait_for_timeout(600)


async def wait_for_store_thinking_nodes(page, min_count=1, timeout_ms=15000):
    """Poll store until thinking nodes exist."""
    for _ in range(timeout_ms // 300):
        await page.wait_for_timeout(300)
        count = await page.evaluate(f"""
            () => {{
                const store = window.__BLUECLAW_STORE__;
                return store && store.thinkingNodes ? store.thinkingNodes.length : 0;
            }}
        """)
        if count >= min_count:
            return count
    return 0


async def wait_for_store_execution_steps(page, min_count=1, timeout_ms=15000):
    """Poll store until execution steps exist."""
    for _ in range(timeout_ms // 300):
        await page.wait_for_timeout(300)
        count = await page.evaluate(f"""
            () => {{
                const store = window.__BLUECLAW_STORE__;
                return store && store.executionSteps ? store.executionSteps.length : 0;
            }}
        """)
        if count >= min_count:
            return count
    return 0


def get_task_id_from_message(msg):
    if not msg:
        return None
    payload = msg.get('payload', {})
    return payload.get('task_id') or payload.get('id')


def get_node_id_from_message(msg):
    if not msg:
        return None
    payload = msg.get('payload', {})
    node = payload.get('node', {})
    return node.get('id')


async def get_pending_node_id(page):
    """Get the first pending thinking node id from store."""
    return await page.evaluate("""() => {
        const store = window.__BLUECLAW_STORE__;
        const nodes = store && store.thinkingNodes ? store.thinkingNodes : [];
        const pending = nodes.filter(n => n.status === 'pending');
        return pending.length > 0 ? pending[0].id : null;
    }""")


async def auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3):
    """Auto-select option A until thinking converges or max rounds reached."""
    for _ in range(max_rounds):
        if any(m.get('type') == 'execution.blueprint_loaded' for m in ws_messages):
            break
        node_id = await get_pending_node_id(page)
        if node_id and task_id:
            await select_option_via_ws(page, task_id, node_id, "A", ws_messages, timeout_ms=8000)
            await page.wait_for_timeout(1500)


# ---------------------------------------------------------------------------
# Q7: Smart Travel Itinerary (Multi-round Intervention)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q07_travel_itinerary(page: Page, ws_messages, console_logs):
    """Q7: Smart Travel Itinerary - Multi-round Intervention Scenario"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q7", "Batch 2", "Smart Travel Itinerary - Multi-round Intervention",
                  "Shanghai night scene planning with replan intervention")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "I am going to Shanghai on business next Wednesday, only free in the evening, want to see the night view, help me plan"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First thinking node: {node_count} node(s) visible")

    if node_count == 0:
        fw.mark_fail("No thinking nodes rendered after task.start")
        return

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)
        await fit_reactflow_view(page)
        node_count2 = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=10000)
        await fw.checkpoint("thinking2", f"After selection: {node_count2} node(s)")

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint loaded: {step_count} step(s)")

    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    await fw.checkpoint("execution", "Execution state captured")
    fw.mark_pass()


# ---------------------------------------------------------------------------
# Q8: PDF Batch Processing (Parallel Steps)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q08_pdf_batch_processing(page: Page, ws_messages, console_logs):
    """Q8: PDF Batch Processing - Parallel Steps Verification"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q8", "Batch 2", "PDF Batch Processing - Parallel Steps",
                  "Convert PDFs to images with parallel execution")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "Help me write a tool that converts all PDFs in a folder to images, keeping the original folder structure"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First node: {node_count} node(s)")

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint: {step_count} step(s)")

    await fit_reactflow_view(page)
    await fw.checkpoint("parallel_check", "Parallel step visual grouping check", status=Status.GAP,
                       notes="Parallel grouping UI gap - visual distinction not implemented")
    fw.mark_gap("Parallel step visual grouping not implemented")


# ---------------------------------------------------------------------------
# Q9: Multi-language Translation + Layout (Multi-stage)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q09_translation_layout(page: Page, ws_messages, console_logs):
    """Q9: Translation + PDF Layout - Multi-stage with Checkpoints"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q9", "Batch 2", "Translation + PDF Layout - Multi-stage",
                  "Chinese to English translation then printable PDF")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "Help me translate a product manual from Chinese to English, then make it into a printable PDF format"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First node: {node_count} node(s)")

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint: {step_count} step(s)")

    await fit_reactflow_view(page)
    await fw.checkpoint("checkpoint_gap", "Stage boundary checkpoint check", status=Status.GAP,
                       notes="Checkpoint UI not implemented")
    fw.mark_gap("Stage boundary checkpoint UI not implemented")


# ---------------------------------------------------------------------------
# Q10: Data Visualization Dashboard (Adaptive Intervention)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q10_data_visualization(page: Page, ws_messages, console_logs):
    """Q10: Data Visualization - Adaptive Intervention"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q10", "Batch 2", "Data Visualization - Adaptive Intervention",
                  "Sales data analysis with trend/issue detection")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "Analyze this sales data and make a visualization dashboard that shows trends and problems"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First node: {node_count} node(s)")

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint: {step_count} step(s)")

    await fit_reactflow_view(page)
    await fw.checkpoint("intervention_gap", "Local intervention check", status=Status.GAP,
                       notes="Local intervention UI not implemented")
    fw.mark_gap("Local intervention (per-chart) not implemented")


# ---------------------------------------------------------------------------
# Q11: Automated API Testing (Tool Layer Verification)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q11_api_testing(page: Page, ws_messages, console_logs):
    """Q11: Automated API Testing - Tool Binding Verification"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q11", "Batch 2", "Automated API Testing - Tool Layer",
                  "Write automated tests for API covering normal and error cases")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "Help me write automated tests for this API, covering normal and error cases"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First node: {node_count} node(s)")

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint: {step_count} step(s)")

    await fit_reactflow_view(page)
    await fw.checkpoint("tool_binding_gap", "Tool binding visual check", status=Status.GAP,
                       notes="Tool binding visual indicators gap")
    fw.mark_gap("Tool binding visual indicators not fully implemented")


# ---------------------------------------------------------------------------
# Q12: Smart Email Processing (Boundary Conditions)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q12_email_processing(page: Page, ws_messages, console_logs):
    """Q12: Smart Email Processing - Boundary Conditions"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q12", "Batch 2", "Smart Email Processing - Boundary Conditions",
                  "Process 50 unread emails with risk detection")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "Help me process these 50 unread emails, categorize them, and reply to important matters"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First node: {node_count} node(s)")

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint: {step_count} step(s)")

    await fit_reactflow_view(page)
    await fw.checkpoint("risk_check_gap", "High-risk email detection check", status=Status.GAP,
                       notes="Risk detection UI not implemented")
    fw.mark_gap("High-risk email forced checkpoint not implemented")


# ---------------------------------------------------------------------------
# Q13: Chrome Extension from Scratch (Long Flow Recovery)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q13_chrome_extension(page: Page, ws_messages, console_logs):
    """Q13: Chrome Extension - Long Flow with Recovery"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q13", "Batch 2", "Chrome Extension - Long Flow Recovery",
                  "Web text selection translation plugin with state persistence")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "Help me develop a Chrome extension from scratch, the function is web text selection translation"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First node: {node_count} node(s)")

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint: {step_count} step(s)")

    await fit_reactflow_view(page)
    await fw.checkpoint("recovery_gap", "Long flow recovery check", status=Status.GAP,
                       notes="State persistence across sessions not implemented")
    fw.mark_gap("Long flow state recovery not implemented")


# ---------------------------------------------------------------------------
# Q14: Cross-platform Content Publishing (Adapter Verification)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q14_xiaohongshu_publish(page: Page, ws_messages, console_logs):
    """Q14: Xiaohongshu Publishing - Adapter Mixed Execution"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("Q14", "Batch 2", "Xiaohongshu Publishing - Adapter Mixed Execution",
                  "Content generation + browser automation adapter")

    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await fw.checkpoint("start", "Initial interface ready")

    user_input = "Help me write a Xiaohongshu note and then directly publish it to my account"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=20000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=20000)
    await fit_reactflow_view(page)
    await fw.checkpoint("thinking1", f"First node: {node_count} node(s)")

    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)

    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=15000)
        await fw.checkpoint("blueprint", f"Blueprint: {step_count} step(s)")

    await fit_reactflow_view(page)
    await fw.checkpoint("adapter_gap", "Adapter visual distinction check", status=Status.GAP,
                       notes="Adapter visual distinction not implemented")
    fw.mark_gap("Adapter visual distinction in execution blueprint not implemented")
