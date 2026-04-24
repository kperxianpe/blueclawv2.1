#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw v2 后端一键启动脚本
自动注入 PYTHONPATH 并启动 WebSocket 服务
"""
import os
import sys
import subprocess

# 将当前目录加入 PYTHONPATH，确保 blueclaw 和 backend 包可被导入
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("PYTHONPATH", PROJECT_ROOT)

main_py = os.path.join(PROJECT_ROOT, "backend", "main.py")
if not os.path.exists(main_py):
    print(f"[ERROR] 找不到后端入口: {main_py}")
    sys.exit(1)

print(f"[INFO] 启动 Blueclaw v2 后端服务...")
print(f"[INFO] PYTHONPATH={PROJECT_ROOT}")
try:
    subprocess.run([sys.executable, main_py], cwd=PROJECT_ROOT)
except KeyboardInterrupt:
    print("\n[INFO] 收到中断信号，后端服务已停止")
