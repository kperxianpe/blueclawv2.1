#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw v2 前端一键启动脚本
自动进入 frontend 目录并运行 npm run dev
"""
import os
import sys
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

if not os.path.exists(os.path.join(FRONTEND_DIR, "package.json")):
    print(f"[ERROR] 找不到前端项目: {FRONTEND_DIR}")
    print("[HINT] 若未安装依赖，请先执行: cd frontend && npm install")
    sys.exit(1)

print(f"[INFO] 启动 Blueclaw v2 前端服务...")
print(f"[INFO] 工作目录: {FRONTEND_DIR}")
try:
    subprocess.run(["npm", "run", "dev"], cwd=FRONTEND_DIR, shell=True)
except KeyboardInterrupt:
    print("\n[INFO] 收到中断信号，前端服务已停止")
