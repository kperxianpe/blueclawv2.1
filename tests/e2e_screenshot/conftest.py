#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest fixtures for Blueclaw E2E screenshot tests
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"


def _check_port(port: int) -> bool:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def backend_process():
    """启动后端服务（如果尚未运行）"""
    if _check_port(8006):
        print("[fixture] Backend already running on port 8006")
        yield None
        return

    print("[fixture] Starting backend...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # 等待后端就绪
    for _ in range(30):
        if _check_port(8006):
            print("[fixture] Backend ready")
            break
        time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError("Backend failed to start within 30s")

    yield proc

    print("[fixture] Stopping backend...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture(scope="session")
def frontend_process():
    """启动前端 dev server（如果尚未运行）"""
    if _check_port(5173):
        print("[fixture] Frontend already running on port 5173")
        yield None
        return

    print("[fixture] Starting frontend...")
    proc = subprocess.Popen(
        "npm run dev",
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    )

    for _ in range(30):
        if _check_port(5173):
            print("[fixture] Frontend ready")
            break
        time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError("Frontend failed to start within 30s")

    yield proc

    print("[fixture] Stopping frontend...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture
async def page_with_services(page, backend_process, frontend_process):
    """
    提供已打开 Blueclaw 首页的 page 对象
    前后端服务已由 session-scoped fixture 启动
    """
    await page.goto("http://localhost:5173")
    # 等待页面加载
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(1)
    yield page
