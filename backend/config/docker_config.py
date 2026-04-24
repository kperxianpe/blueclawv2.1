#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker Sandbox 配置 - Week 20.5
"""

# 沙箱容器镜像配置（可配置化，而非硬编码）
SANDBOX_IMAGE = "blueclaw/sandbox:latest"  # 预装常用库的自定义镜像
FALLBACK_IMAGE = "python:3.11-slim"  # 回退镜像

# 容器资源限制
DEFAULT_TIMEOUT = 30  # 默认超时 30 秒
MEMORY_LIMIT = "512m"
CPU_QUOTA = 100000

# 沙箱工作目录
SANDBOX_WORKDIR = "/workspace"

# 镜像构建脚本 (Dockerfile.sandbox)
# 使用说明：
# 1. 保存以下内容到 Dockerfile.sandbox
# 2. 运行: docker build -t blueclaw/sandbox:latest -f Dockerfile.sandbox .
DOCKERFILE_CONTENT = """
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    gcc \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# 安装常用 Python 库
RUN pip install --no-cache-dir \\
    requests \\
    beautifulsoup4 \\
    pandas \\
    numpy \\
    pillow \\
    pyyaml \\
    httpx \\
    lxml

WORKDIR /workspace

# 默认命令：保持容器运行
CMD ["sleep", "3600"]
"""

# 支持的编程语言
SUPPORTED_LANGUAGES = {
    "python": {
        "command": "python3",
        "file_extension": ".py",
        "default_filename": "script.py"
    },
    "bash": {
        "command": "bash",
        "file_extension": ".sh",
        "default_filename": "script.sh"
    },
    "javascript": {
        "command": "node",
        "file_extension": ".js",
        "default_filename": "script.js"
    }
}
