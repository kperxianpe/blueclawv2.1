#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw 3 分钟自检脚本

用途：快速判断当前代码状态，区分"环境配置问题"和"真实功能缺失"。
用法：cd blueclawv2 && python blueclaw/tests/self_check.py

Windows 注意：若控制台输出乱码，先执行 chcp 65001
"""

import sys
import os
import subprocess
from pathlib import Path

# Windows GBK 控制台兼容
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 自动推断项目根目录
SELF = Path(__file__).resolve()
PROJECT_ROOT = SELF.parent.parent.parent  # blueclawv2/
BLUECLAW_DIR = PROJECT_ROOT / "blueclaw"

# 确保项目根目录在 sys.path 中，使 find_spec 能找到 blueclaw
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

results = []


def check(name, condition, fix=""):
    results.append((name, condition, fix))
    status = "[OK]" if condition else "[FAIL]"
    print(f"{status} {name}")
    if not condition and fix:
        print(f"    -> {fix}")


def main():
    print("=" * 60)
    print("Blueclaw 3 分钟自检")
    print(f"项目根目录: {PROJECT_ROOT}")
    print("=" * 60)

    # --- 环境层 ---
    print("\n[环境层]")
    check(
        "blueclaw/__init__.py 存在",
        (BLUECLAW_DIR / "__init__.py").exists(),
        f"touch {BLUECLAW_DIR}/__init__.py",
    )

    check(
        "PYTHONPATH 包含项目根目录",
        str(PROJECT_ROOT) in sys.path or str(PROJECT_ROOT) in os.getenv("PYTHONPATH", ""),
        f"set PYTHONPATH={PROJECT_ROOT};%PYTHONPATH%",
    )

    check(
        "websockets 已安装",
        __import__("importlib").util.find_spec("websockets") is not None,
        "pip install websockets",
    )

    check(
        "playwright 已安装",
        __import__("importlib").util.find_spec("playwright") is not None,
        "pip install playwright",
    )

    # Playwright 浏览器检查（静默）
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser_ok = hasattr(p, "chromium")
    except Exception:
        browser_ok = False
    check(
        "Playwright Chromium 浏览器已下载",
        browser_ok,
        "playwright install chromium",
    )

    # --- 代码层 ---
    print("\n[代码层]")
    check(
        "blueclaw/adapter/ 目录存在",
        (BLUECLAW_DIR / "adapter").is_dir(),
        "adapter 目录缺失，需从 git 恢复",
    )

    adapter_modules = [
        "blueclaw.adapter.manager",
        "blueclaw.adapter.models",
        "blueclaw.adapter.state",
        "blueclaw.adapter.adapters.web",
        "blueclaw.adapter.adapters.ide",
    ]
    import importlib.util
    for mod in adapter_modules:
        spec = importlib.util.find_spec(mod)
        check(
            f"{mod} 可 import",
            spec is not None,
            f"创建 {mod.replace('.', '/')}.py 骨架",
        )

    # --- 对接层 ---
    print("\n[对接层 - ExecutionEngine-Adapter]")

    ee_path = BLUECLAW_DIR / "core" / "execution_engine.py"
    if ee_path.exists():
        content = ee_path.read_text(encoding="utf-8")
        has_adapter_import = "AdapterManager" in content
        has_screenshot_hook = "_maybe_capture_screenshot" in content
    else:
        has_adapter_import = has_screenshot_hook = False

    check(
        "ExecutionEngine 已导入 AdapterManager",
        has_adapter_import,
        "execution_engine.py 需 from blueclaw.adapter.manager import AdapterManager",
    )
    check(
        "ExecutionEngine 含截图钩子",
        has_screenshot_hook,
        "execution_engine.py 需添加 _maybe_capture_screenshot 方法",
    )

    # WebSocket 干预 handlers
    router_paths = [
        BLUECLAW_DIR / "backend" / "websocket" / "message_router.py",
        PROJECT_ROOT / "backend" / "websocket" / "message_router.py",
    ]
    router_content = ""
    for p in router_paths:
        if p.exists():
            router_content = p.read_text(encoding="utf-8")
            break

    has_freeze = "freeze_request" in router_content
    has_retry = "retry_step" in router_content
    has_replan = "request_replan" in router_content

    check(
        "WebSocket freeze_request handler 已注册",
        has_freeze,
        "backend/websocket/message_router.py 需注册 freeze_request",
    )
    check(
        "WebSocket retry_step handler 已注册",
        has_retry,
        "backend/websocket/message_router.py 需注册 retry_step",
    )
    check(
        "WebSocket request_replan handler 已注册",
        has_replan,
        "backend/websocket/message_router.py 需注册 request_replan",
    )

    # --- 测试层 ---
    print("\n[测试层]")
    adapter_test_dir = BLUECLAW_DIR / "adapter" / "tests"
    check(
        "adapter/tests/ 目录存在",
        adapter_test_dir.is_dir(),
        "adapter 测试目录缺失",
    )

    # 快速运行核心测试
    if adapter_test_dir.is_dir():
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(adapter_test_dir / "core" / "test_manager.py"), "-q", "--tb=no"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            passed = "passed" in result.stdout.lower()
            check(
                "adapter core tests 通过",
                passed and result.returncode == 0,
                f"pytest 输出: {result.stdout.strip()[-100:] if result.stdout else 'N/A'}",
            )
        except Exception as e:
            check("adapter core tests 通过", False, f"运行失败: {e}")
    else:
        check("adapter core tests 通过", False, "测试目录不存在")

    # --- 总结 ---
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    pct = passed / total * 100 if total else 0
    print(f"自检结果: {passed}/{total} 通过 ({pct:.0f}%)")

    if passed == total:
        print("\n环境就绪，建议运行:")
        print(f"  cd {PROJECT_ROOT}")
        print("  python -m pytest blueclaw/adapter/tests/core -q")
        print("  python -m pytest blueclaw/adapter/tests/web -q")
        return 0
    elif passed >= total * 0.7:
        print("\n基本环境 OK，剩余问题可按修复提示逐个解决")
        return 0
    else:
        print("\n环境问题严重，先按 [环境层] 修复提示处理")
        return 1


if __name__ == "__main__":
    sys.exit(main())
