#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw v2.5 后端统一入口
FastAPI + WebSocket 混合服务

Endpoints:
  HTTP REST : http://localhost:8006/api/ide/*  (IDE filesystem/runner/kimicode)
  WS Main   : ws://localhost:8006/ws          (task lifecycle + adapter runtime)
  WS IDE    : ws://localhost:8006/ws/ide      (IDE real-time push)
"""
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载环境变量
from dotenv import load_dotenv
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"), override=True)
print(f"[Main] Loaded .env from {os.path.join(project_root, '.env')}")
print(f"[Main] KIMI_API_KEY set: {'Yes' if os.getenv('KIMI_API_KEY') else 'No'}")

import uvicorn
from core.task_manager import task_manager
from core.checkpoint import checkpoint_manager
from unified_server import app, unified_server


def main():
    # 1. 恢复之前的任务（临时跳过以加速启动）
    # print("Restoring tasks from checkpoints...")
    # await checkpoint_manager.restore_all_tasks(task_manager)

    # 2. 设置 TaskManager 和 MessageRouter 的服务器引用
    task_manager.set_server(unified_server)
    from websocket.message_router import router
    router.set_websocket_server(unified_server)
    print("[Main] TaskManager and MessageRouter server references set")

    # 3. 启动统一服务（FastAPI HTTP + WebSocket）
    port = int(os.environ.get('PORT', 8006))
    print(f"[Main] Starting Blueclaw v2.5 Unified Server on port {port}")
    print(f"[Main]   HTTP REST: http://localhost:{port}/api/ide/*")
    print(f"[Main]   WS Main  : ws://localhost:{port}/ws")
    print(f"[Main]   WS IDE   : ws://localhost:{port}/ws/ide")

    uvicorn.run(
        "unified_server:app",
        host="localhost",
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Main] Server stopped")
