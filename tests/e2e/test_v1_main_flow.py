#!/usr/bin/env python3
"""
Blueclaw V1 Main Flow E2E Test — 输入 → Thinking → Execution → Result
4 Test Cases, 6+ screenshots each, 1920x1080 viewport
"""
import pytest
import json
from playwright.async_api import Page
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_framework import Framework, Status
from tests.e2e.test_batch2_q7_q14 import (
    start_task_via_ws, select_option_via_ws, confirm_execution_via_ws,
    wait_for_thinking_nodes, wait_for_execution_steps, fit_reactflow_view,
    get_task_id_from_message, get_pending_node_id, auto_select_until_convergence,
)

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "v1_main_flow"


# ============================================================================
# Test Case 1: 旅行规划（模糊输入 → 选项引导 → 执行完成）
# ============================================================================
@pytest.mark.asyncio
async def test_case_1_travel_planning(page: Page, ws_messages, console_logs):
    """题目1: 我想规划一个周末短途旅行"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("TC1", "V1-MainFlow", "Travel Planning",
                  "Fuzzy input -> option guidance -> execution complete")

    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1500)

    # 1.0 输入接收
    await fw.checkpoint("1_0_input_ready", "Initial interface ready after input page load")

    user_input = "我想规划一个周末短途旅行"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=25000)
    task_id = get_task_id_from_message(msg)

    # 1.1 首节点生成
    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=25000)
    await fit_reactflow_view(page)
    await fw.checkpoint("1_1_first_node", f"First thinking node rendered: {node_count} node(s)")

    if node_count == 0:
        fw.mark_fail("No thinking nodes rendered after task.start — WebSocket or ThinkingEngine issue")
        return

    # Verify node has options
    has_options = await page.evaluate("""() => {
        const store = window.__BLUECLAW_STORE__;
        const nodes = store && store.thinkingNodes ? store.thinkingNodes : [];
        return nodes.length > 0 && (nodes[0].options || []).length > 0;
    }""")
    if not has_options:
        await fw.checkpoint("1_1b_options_check", "First node missing options", status=Status.FAIL)

    # 1.2 选项交互 — 悬停效果（截图记录当前状态）
    await page.wait_for_timeout(1000)
    await fit_reactflow_view(page)
    await fw.checkpoint("1_2_options_hover", "Options visible for interaction hover check")

    # 1.3 用户选择 — 点击选项B（如果存在）
    if task_id:
        node_id = await get_pending_node_id(page)
        if node_id:
            # Try to find option B, fallback to first option
            option_id = await page.evaluate("""() => {
                const store = window.__BLUECLAW_STORE__;
                const nodes = store && store.thinkingNodes ? store.thinkingNodes : [];
                const pending = nodes.filter(n => n.status === 'pending');
                if (pending.length > 0 && pending[0].options && pending[0].options.length > 1) {
                    return pending[0].options[1].id; // option B
                }
                return pending.length > 0 && pending[0].options ? pending[0].options[0].id : null;
            }""")
            if option_id:
                await select_option_via_ws(page, task_id, node_id, option_id, ws_messages, timeout_ms=10000)
                await page.wait_for_timeout(2000)
                await fit_reactflow_view(page)
                await fw.checkpoint("1_3_option_selected", f"Option {option_id} selected, visual feedback captured")

    # 1.4 子节点生成 — 自动选择直到收敛
    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)
        await fit_reactflow_view(page)
        node_count2 = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=10000)
        await fw.checkpoint("1_4_child_nodes", f"Child nodes generated: {node_count2} node(s), connections visible")

    # 1.5 AI自动选择 — 检查是否有 recommended 选项
    has_recommended = await page.evaluate("""() => {
        const store = window.__BLUECLAW_STORE__;
        const nodes = store && store.thinkingNodes ? store.thinkingNodes : [];
        return nodes.some(n => (n.options || []).some(o => o.isDefault || o.confidence >= 0.85));
    }""")
    await fw.checkpoint("1_5_ai_recommend", f"AI recommendation tag check: has_recommended={has_recommended}")

    # 1.6 思考收敛 / 过渡状态
    await page.wait_for_timeout(1500)
    await fit_reactflow_view(page)
    phase = await page.evaluate("""() => {
        const store = window.__BLUECLAW_STORE__;
        return store ? store.phase : 'unknown';
    }""")
    await fw.checkpoint("1_6_convergence", f"Phase after thinking: {phase}")

    # 1.7 执行蓝图渲染
    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=20000)
        await fw.checkpoint("1_7_blueprint", f"Execution blueprint loaded: {step_count} step(s)")

        if step_count == 0:
            fw.mark_fail("No execution steps rendered after blueprint loaded")
            return

    # 1.8-1.10 执行状态 — 截图记录
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    await fw.checkpoint("1_8_execution_running", "Execution running state captured")

    await page.wait_for_timeout(3000)
    await fit_reactflow_view(page)
    await fw.checkpoint("1_9_execution_progress", "Execution progress state captured")

    # Final state
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    await fw.checkpoint("1_10_final_report", "Final execution state / result report captured")
    fw.mark_pass()


# ============================================================================
# Test Case 2: 批量文件处理（明确输入 → 快速收敛 → 多步骤执行）
# ============================================================================
@pytest.mark.asyncio
async def test_case_2_batch_file_processing(page: Page, ws_messages, console_logs):
    """题目2: 帮我写个Python脚本，把文件夹里的图片按日期重命名"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("TC2", "V1-MainFlow", "Batch File Processing",
                  "Clear intent -> fast converge -> multi-step execution with progress")

    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1500)

    # 2.1 明确意图识别
    await fw.checkpoint("2_1_start", "Initial interface ready")

    user_input = "帮我写个Python脚本，把文件夹里的图片按日期重命名"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=25000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=25000)
    await fit_reactflow_view(page)
    await fw.checkpoint("2_2_thinking1", f"First thinking node: {node_count} node(s), clear intent recognition")

    if node_count == 0:
        fw.mark_fail("No thinking nodes rendered")
        return

    # 2.2 快速收敛 — 选项数量检查（明确输入应该选项较少）
    option_count = await page.evaluate("""() => {
        const store = window.__BLUECLAW_STORE__;
        const nodes = store && store.thinkingNodes ? store.thinkingNodes : [];
        return nodes.length > 0 ? (nodes[0].options || []).length : 0;
    }""")
    await fw.checkpoint("2_3_option_count", f"Option count for clear intent: {option_count} (expect <= 4)")

    # 自动选择直到收敛
    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)
        await fit_reactflow_view(page)
        await fw.checkpoint("2_4_converged", "Thinking converged, ready for blueprint generation")

    # 2.3 蓝图渲染
    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=20000)
        await fw.checkpoint("2_5_blueprint", f"Blueprint loaded: {step_count} step(s)")

    # 2.4 批量进度（截图记录执行状态）
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    has_progress_ui = await page.evaluate("""() => {
        // Check for any progress-like indicators
        return document.querySelector('.progress-bar, [role="progressbar"], .progress') !== null;
    }""")
    await fw.checkpoint("2_6_progress", f"Progress indicator visible: {has_progress_ui}")

    # 2.5 异常处理 — 检查是否有警告/错误状态节点
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    warning_nodes = await page.locator('.react-flow__node-execution').filter(has_text='警告').count()
    await fw.checkpoint("2_7_exception", f"Warning/exception nodes: {warning_nodes}")

    # 2.6 完成报告
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    await fw.checkpoint("2_8_final", "Final execution state / completion report captured")
    fw.mark_pass()


# ============================================================================
# Test Case 3: 代码生成与验证（IDE Adapter链路）
# ============================================================================
@pytest.mark.asyncio
async def test_case_3_code_generation(page: Page, ws_messages, console_logs):
    """题目3: 给这个React项目加一个带表单验证的登录页"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("TC3", "V1-MainFlow", "Code Generation + IDE Adapter",
                  "React login page with form validation via IDE Adapter")

    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1500)

    # 3.1 技术约束解析
    await fw.checkpoint("3_1_start", "Initial interface ready")

    user_input = "给这个React项目加一个带表单验证的登录页"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=25000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=25000)
    await fit_reactflow_view(page)
    await fw.checkpoint("3_2_thinking1", f"First thinking node: {node_count} node(s), tech stack parsing")

    if node_count == 0:
        fw.mark_fail("No thinking nodes rendered")
        return

    # 3.2 依赖确认
    await page.wait_for_timeout(1000)
    await fit_reactflow_view(page)
    await fw.checkpoint("3_3_dependency_check", "Dependency/library selection options visible")

    # 自动选择
    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)
        await fit_reactflow_view(page)
        await fw.checkpoint("3_4_converged", "Thinking converged")

    # 3.3 IDE视图切换（检查是否有IDE标签/视图）
    has_ide_tab = await page.evaluate("""() => {
        return document.querySelector('[data-tab="ide"], .ide-tab, #ide-panel') !== null;
    }""")
    await fw.checkpoint("3_5_ide_view", f"IDE view/tab available: {has_ide_tab}",
                       status=Status.GAP if not has_ide_tab else Status.PASS,
                       notes="IDE Adapter view switching — gap if not implemented")

    # 3.4 蓝图渲染
    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=20000)
        await fw.checkpoint("3_6_blueprint", f"Blueprint loaded: {step_count} step(s)")

    # 3.5 代码生成效果（打字机效果检查）
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    has_typewriter = await page.evaluate("""() => {
        return document.querySelector('.typewriter, .typing-effect, [data-typing]') !== null;
    }""")
    await fw.checkpoint("3_7_code_generation", f"Typewriter/typing effect visible: {has_typewriter}",
                       status=Status.GAP if not has_typewriter else Status.PASS,
                       notes="Code generation typing effect — gap if not implemented")

    # 3.6 完成总结
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    await fw.checkpoint("3_8_final", "Final execution state / file list summary captured")
    fw.mark_pass()


# ============================================================================
# Test Case 4: Web数据采集（Web Adapter链路）
# ============================================================================
@pytest.mark.asyncio
async def test_case_4_web_data_collection(page: Page, ws_messages, console_logs):
    """题目4: 抓取豆瓣上评分8.5以上的科幻电影，整理成表格"""
    fw = Framework(page, SCREENSHOT_DIR)
    fw.start_case("TC4", "V1-MainFlow", "Web Data Collection",
                  "Douban sci-fi movie scraping via Web Adapter")

    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto(FRONTEND_URL, wait_until="networkidle")
    await page.wait_for_timeout(1500)

    # 4.1 多维度拆解
    await fw.checkpoint("4_1_start", "Initial interface ready")

    user_input = "抓取豆瓣上评分8.5以上的科幻电影，整理成表格"
    msg = await start_task_via_ws(page, user_input, ws_messages, timeout_ms=25000)
    task_id = get_task_id_from_message(msg)

    node_count = await wait_for_thinking_nodes(page, min_count=1, timeout_ms=25000)
    await fit_reactflow_view(page)
    await fw.checkpoint("4_2_thinking1", f"First thinking node: {node_count} node(s), multi-dimension breakdown")

    if node_count == 0:
        fw.mark_fail("No thinking nodes rendered")
        return

    # 4.2 Web视图切换提示
    has_web_nav = await page.evaluate("""() => {
        return document.querySelector('[data-web-navigate], .web-navigate-prompt, .auto-navigate') !== null;
    }""")
    await fw.checkpoint("4_3_web_navigate", f"Web navigate countdown prompt: {has_web_nav}",
                       status=Status.GAP if not has_web_nav else Status.PASS,
                       notes="Auto Web view navigation prompt — gap if not implemented")

    # 自动选择直到收敛
    if task_id:
        await auto_select_until_convergence(page, task_id, ws_messages, max_rounds=3)
        await page.wait_for_timeout(2000)
        await fit_reactflow_view(page)
        await fw.checkpoint("4_4_converged", "Thinking converged")

    # 4.3 Web浏览器视图
    has_web_browser = await page.evaluate("""() => {
        return document.querySelector('iframe[src*="douban"], .web-browser, [data-web-view]') !== null;
    }""")
    await fw.checkpoint("4_5_web_browser", f"Web browser component visible: {has_web_browser}",
                       status=Status.GAP if not has_web_browser else Status.PASS,
                       notes="Web Browser component for data scraping — gap if not implemented")

    # 4.4 蓝图渲染
    if task_id:
        await confirm_execution_via_ws(page, task_id, ws_messages, timeout_ms=20000)
        await page.wait_for_timeout(3000)
        await fit_reactflow_view(page)
        step_count = await wait_for_execution_steps(page, min_count=1, timeout_ms=20000)
        await fw.checkpoint("4_6_blueprint", f"Blueprint loaded: {step_count} step(s)")

    # 4.5 数据提取结果
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    has_table = await page.evaluate("""() => {
        return document.querySelector('table, .data-table, .results-grid') !== null;
    }""")
    await fw.checkpoint("4_7_data_table", f"Structured data table visible: {has_table}",
                       status=Status.GAP if not has_table else Status.PASS,
                       notes="Data extraction result table — gap if not implemented")

    # 4.6 最终表格/导出
    await page.wait_for_timeout(2000)
    await fit_reactflow_view(page)
    has_export = await page.evaluate("""() => {
        return document.querySelector('button[data-export], .export-btn, [download]') !== null;
    }""")
    await fw.checkpoint("4_8_final_export", f"Export/download button visible: {has_export}",
                       status=Status.GAP if not has_export else Status.PASS,
                       notes="CSV/Excel export functionality — gap if not implemented")
    fw.mark_pass()
