#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw v2.5 一键端到端运行脚本
=================================
功能：自动启动前后端服务 → 打开浏览器 → 输入任务 → 跑通思考蓝图 → 执行蓝图 → 截图存档

运行方式:
    cd blueclawv2
    python run_blueclaw.py

环境要求:
    pip install playwright Pillow
    python -m playwright install chromium
    前端: cd frontend && npm install

特性:
    - 自动检测端口 8006/5173，服务已运行则复用，未运行则自动启动
    - 使用 Playwright 同步 API（避免 pytest-asyncio event loop 冲突）
    - 全流程截图保存到 screenshots/YYYYmmdd_HHMMSS/ 目录
    - Ctrl+C 优雅退出，自动清理子进程
"""

import os
import sys
import time
import socket
import subprocess
import threading
import signal
from datetime import datetime
from pathlib import Path

# ── 项目路径 ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"          # 优先使用 frontend 目录
ALT_FRONTEND_DIR = PROJECT_ROOT / "buleclawv1-frontword"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"

# ── 全局进程列表（用于清理）───────────────────────────
PROCESSES = []
SHUTDOWN = False


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def _port_ready(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _wait_for_port(port: int, timeout: int = 30) -> bool:
    for _ in range(timeout * 2):
        if _port_ready(port):
            return True
        time.sleep(0.5)
    return False


def _drain_pipe(proc: subprocess.Popen, prefix: str):
    """后台线程读取子进程 stdout，防止缓冲区满阻塞"""
    try:
        for line in proc.stdout:
            if SHUTDOWN:
                break
            text = line.strip()
            if text:
                log(f"[{prefix}] {text}")
    except Exception:
        pass


def start_backend() -> subprocess.Popen | None:
    if _port_ready(8006):
        log("后端服务已在 8006 端口运行，直接复用")
        return None

    log("启动后端服务...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    PROCESSES.append(proc)
    threading.Thread(target=_drain_pipe, args=(proc, "Backend"), daemon=True).start()

    if not _wait_for_port(8006, timeout=30):
        log("ERROR: 后端服务未能在 30s 内就绪")
        return proc
    log("后端服务就绪 (ws://127.0.0.1:8006/ws)")
    return proc


def start_frontend() -> subprocess.Popen | None:
    if _port_ready(5173):
        log("前端服务已在 5173 端口运行，直接复用")
        return None

    # 选择有效的前端目录
    fe_dir = FRONTEND_DIR if (FRONTEND_DIR / "package.json").exists() else ALT_FRONTEND_DIR
    if not (fe_dir / "package.json").exists():
        log(f"ERROR: 找不到前端项目 (尝试了 {FRONTEND_DIR}, {ALT_FRONTEND_DIR})")
        return None

    log(f"启动前端服务... (目录: {fe_dir.name})")
    env = os.environ.copy()
    env["VITE_WS_URL"] = "ws://127.0.0.1:8006/ws"

    # Windows 上优先找 npm.cmd
    npm = "npm"
    npm_cmd = Path(r"C:\Program Files\nodejs\npm.cmd")
    if npm_cmd.exists():
        npm = str(npm_cmd)

    proc = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", "5173", "--host", "127.0.0.1"],
        cwd=fe_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=(sys.platform == "win32"),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    PROCESSES.append(proc)
    threading.Thread(target=_drain_pipe, args=(proc, "Frontend"), daemon=True).start()

    if not _wait_for_port(5173, timeout=30):
        log("ERROR: 前端服务未能在 30s 内就绪")
        return proc
    log("前端服务就绪 (http://127.0.0.1:5173)")
    return proc


def cleanup():
    """清理所有子进程"""
    global SHUTDOWN
    SHUTDOWN = True
    log("正在清理子进程...")
    for proc in PROCESSES:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    log("清理完成")


def get_store_state(page):
    """读取前端 Redux/Zustand store 状态（如果暴露），失败不影响主流程"""
    try:
        return page.evaluate("""() => {
            try {
                const store = window.__BLUECLAW_STORE__;
                if (!store) return { phase: 'unknown' };
                // Zustand: store() 或 store.getState()
                let s = (typeof store === 'function') ? store() : (store.getState ? store.getState() : store);
                return {
                    phase: s.phase || 'unknown',
                    thinkingCount: s.thinkingNodes?.length || s.thinkingNodeCount || 0,
                    executionCount: s.executionSteps?.length || s.executionStepCount || 0,
                };
            } catch (e) {
                return { phase: 'error', error: e.message };
            }
        }""")
    except Exception as e:
        return { "phase": "error", "error": str(e) }


def run_e2e(task: str = "帮我写一篇关于人工智能的公众号文章") -> int:
    """主流程：打开浏览器 → 输入任务 → 思考蓝图 → 执行蓝图 → 截图"""
    from playwright.sync_api import sync_playwright

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = SCREENSHOT_DIR / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"截图输出目录: {out_dir}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # 收集浏览器控制台日志
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        try:
            # ── S0: 打开页面 ──────────────────────────────
            log("打开 http://127.0.0.1:5173 ...")
            page.goto("http://127.0.0.1:5173")
            page.wait_for_timeout(2000)
            page.screenshot(path=str(out_dir / "S0_initial.png"))
            log("S0_initial.png 已保存")

            # ── S1: 输入任务 ──────────────────────────────
            log(f"输入任务: {task}")
            # 兼容多种输入框
            input_selectors = ["input", "textarea", "[placeholder*='任务']", "[placeholder*='输入']"]
            input_found = False
            for sel in input_selectors:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.fill(task)
                    input_found = True
                    break
            if not input_found:
                log("WARNING: 未找到输入框，尝试直接定位第一个 input")
                page.locator("input").first.fill(task)
            page.wait_for_timeout(500)
            page.screenshot(path=str(out_dir / "S1_input_filled.png"))
            log("S1_input_filled.png 已保存")

            # ── S2: 提交任务 ──────────────────────────────
            log("点击发送按钮...")
            btn_selectors = [
                "button.bg-blue-500",
                "button:has-text('开始')",
                "button:has-text('发送')",
                "button:has-text('提交')",
                "button[type='submit']",
            ]
            btn_found = False
            for sel in btn_selectors:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    btn_found = True
                    break
            if not btn_found:
                log("WARNING: 未找到发送按钮，尝试回车")
                page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            page.screenshot(path=str(out_dir / "S2_submitted.png"))
            log("S2_submitted.png 已保存")

            # ── S3: 等待第一个思考节点 ─────────────────────
            log("等待第一个思考节点生成（LLM 首次调用，可能需 10~60s）...")
            try:
                page.wait_for_selector("[data-nodeid^='thinking']", timeout=90000)
                page.wait_for_timeout(1000)
                page.screenshot(path=str(out_dir / "S3_first_thinking_node.png"))
                log("S3_first_thinking_node.png 已保存")
                state = get_store_state(page)
                log(f"Store 状态: {state}")
            except Exception as e:
                log(f"ERROR: 思考节点未在 90s 内出现: {e}")
                page.screenshot(path=str(out_dir / "S3_timeout.png"))
                return 1

            # ── S4: 展开思考节点 ──────────────────────────
            log("展开思考节点...")
            try:
                # 优先点击节点内的 ChevronDown / 标题区域来展开
                expanders = [
                    "[data-nodeid^='thinking'] svg.lucide-chevron-down",
                    "[data-nodeid^='thinking'] .cursor-pointer",
                    "[data-nodeid^='thinking'] div[class*='cursor-pointer']",
                    "[data-id^='thinking'] .cursor-pointer",
                ]
                clicked = False
                for sel in expanders:
                    el = page.locator(sel).first
                    if el.count() > 0 and el.is_visible():
                        el.click()
                        clicked = True
                        log(f"点击 {sel} 展开")
                        break
                if not clicked:
                    # fallback: 点击节点中心坐标（避开 React Flow 拖拽）
                    node = page.locator("[data-nodeid^='thinking']").first
                    box = node.bounding_box()
                    if box:
                        # 点击节点上半部分（标题区域）
                        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + 20)
                        log("点击节点标题区域展开")
            except Exception as e:
                log(f"WARNING: 展开节点失败: {e}")
            page.wait_for_timeout(1500)
            page.screenshot(path=str(out_dir / "S4_expanded.png"))
            log("S4_expanded.png 已保存")

            # ── S5: 自动处理所有待选择的思考节点 ───────────
            log("开始自动选择思考节点...")
            for round_idx in range(10):   # 最多处理 10 轮思考节点
                # 等待当前展开的选项出现（只匹配 bg-gray-800，避免匹配 disabled 的重新思考按钮）
                option_selectors = [
                    "[data-nodeid^='thinking'] button[class*='bg-gray-800']",
                    "[data-id^='thinking'] button[class*='bg-gray-800']",
                ]
                clicked_option = False
                for sel in option_selectors:
                    loc = page.locator(sel)
                    cnt = loc.count()
                    if cnt >= 1:
                        # 确保点击的是 enabled 的选项按钮
                        for idx in range(min(cnt, 5)):
                            btn = loc.nth(idx)
                            if btn.is_enabled() and btn.is_visible():
                                txt = btn.inner_text()
                                if txt and "重新思考" not in txt:
                                    btn.click()
                                    clicked_option = True
                                    log(f"第 {round_idx + 1} 轮: 已点击选项 [{idx}]: {txt[:30]}")
                                    break
                        if clicked_option:
                            break

                if not clicked_option:
                    # 兜底：找节点内所有可见 enabled button（排除干涉/自定义输入按钮）
                    all_btns = page.locator("[data-nodeid^='thinking'] button, [data-id^='thinking'] button").all()
                    for b in all_btns:
                        if not b.is_visible() or not b.is_enabled():
                            continue
                        txt = b.inner_text()
                        if txt and "重新思考" not in txt and "取消" not in txt and "确认" not in txt and "其他" not in txt:
                            b.click()
                            clicked_option = True
                            log(f"第 {round_idx + 1} 轮: 已点击可用按钮: {txt[:20]}")
                            break

                if not clicked_option:
                    log("WARNING: 未找到任何可点击的选项按钮，结束选择")
                    break

                page.wait_for_timeout(3000)
                page.screenshot(path=str(out_dir / f"S5_round{round_idx + 1}_selected.png"))
                log(f"S5_round{round_idx + 1}_selected.png 已保存")

                # 等待后端响应（新节点或执行阶段）
                log("等待后端响应...")
                found_next = False
                for i in range(60):       # 最多等 30s
                    state = get_store_state(page)
                    if state.get("phase") == "execution":
                        log(f"执行阶段已到达！")
                        found_next = True
                        break
                    if page.locator("[data-nodeid^='execution']").count() > 0:
                        log(f"检测到执行节点")
                        found_next = True
                        break
                    # 检测是否有新的 pending 思考节点（通过选项按钮出现判断）
                    pending_found = False
                    for sel in option_selectors:
                        loc = page.locator(sel)
                        for idx in range(min(loc.count(), 5)):
                            if loc.nth(idx).is_enabled():
                                pending_found = True
                                break
                        if pending_found:
                            break
                    if pending_found and i > 3:
                        log(f"检测到新的待选择思考节点")
                        found_next = True
                        break
                    time.sleep(0.5)

                if not found_next:
                    log("本轮未检测到新节点或执行阶段，结束选择")
                    break

                # 如果已进入执行阶段，退出循环
                state = get_store_state(page)
                if state.get("phase") == "execution" or page.locator("[data-nodeid^='execution']").count() > 0:
                    break

                # 否则继续下一轮（新思考节点已出现，需要展开）
                log("准备处理下一个思考节点...")
                page.wait_for_timeout(2000)

            # ── S6: 执行阶段截图 ──────────────────────────
            page.wait_for_timeout(2000)
            page.screenshot(path=str(out_dir / "S6_execution_or_next.png"))
            log("S6_execution_or_next.png 已保存")

            # ── S7: 如果已进入执行阶段，等待步骤完成 ───────
            state = get_store_state(page)
            has_execution = state.get("phase") == "execution" or page.locator("[data-nodeid^='execution']").count() > 0
            if has_execution:
                log("等待执行步骤推进...")
                for i in range(60):
                    state = get_store_state(page)
                    steps = state.get("executionCount", 0)
                    if steps >= 2:
                        log(f"检测到 {steps} 个执行步骤")
                        break
                    time.sleep(0.5)
                page.wait_for_timeout(2000)
                page.screenshot(path=str(out_dir / "S7_execution_progress.png"))
                log("S7_execution_progress.png 已保存")
            else:
                log("WARNING: 未检测到执行阶段，可能仍在思考中")
                page.screenshot(path=str(out_dir / "S7_no_execution.png"))

            # ── 保存控制台日志 ────────────────────────────
            log_path = out_dir / "console_logs.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in console_logs:
                    f.write(line + "\n")
            log(f"控制台日志已保存: {log_path}")

            browser.close()
            log("=" * 50)
            log("全流程运行完成！")
            log(f"截图目录: {out_dir}")
            log("=" * 50)
            return 0

        except Exception as e:
            log(f"ERROR: 运行过程中出现异常: {e}")
            page.screenshot(path=str(out_dir / "ERROR.png"))
            import traceback
            traceback.print_exc()
            return 1
        finally:
            try:
                browser.close()
            except Exception:
                pass


def main():
    # 注册信号处理（Windows 也支持 KeyboardInterrupt）
    def signal_handler(sig, frame):
        log("收到中断信号，正在退出...")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    log("=" * 50)
    log("Blueclaw v2.5 一键端到端运行脚本")
    log("=" * 50)

    # 1. 启动后端
    backend_proc = start_backend()
    if backend_proc is not None and backend_proc.poll() is not None:
        log("后端启动失败，退出")
        return 1

    # 2. 启动前端
    frontend_proc = start_frontend()
    if frontend_proc is not None and frontend_proc.poll() is not None:
        log("前端启动失败，退出")
        cleanup()
        return 1

    # 3. 运行 E2E
    task = "帮我写一篇关于人工智能的公众号文章"
    if len(sys.argv) > 1:
        task = sys.argv[1]
    exit_code = run_e2e(task)

    # 4. 清理（如果服务是我们启动的）
    cleanup()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
