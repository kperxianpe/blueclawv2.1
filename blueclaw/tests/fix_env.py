#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键修复测试环境（Windows / 通用）"""

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BLUECLAW = ROOT / "blueclaw"


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or str(ROOT))
    return result.returncode == 0


def ensure_init(path: Path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        print(f"[OK] 创建 {path}")
    else:
        print(f"[OK] 已存在 {path}")


def main():
    print("=" * 60)
    print("Blueclaw 测试环境一键修复")
    print(f"项目根目录: {ROOT}")
    print("=" * 60)

    # 1. 补齐 __init__.py
    print("\n[1/4] 检查 __init__.py...")
    ensure_init(BLUECLAW / "__init__.py")

    # 2. 安装依赖
    print("\n[2/4] 安装依赖...")
    run(f"{sys.executable} -m pip install websockets playwright -q")

    # 3. Playwright 浏览器
    print("\n[3/4] 检查 Playwright 浏览器...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            if hasattr(p, "chromium"):
                print("[OK] Chromium 已安装")
            else:
                raise RuntimeError("Chromium not found")
    except Exception:
        print("[INFO] 正在下载 Chromium...")
        run("playwright install chromium")

    # 4. 创建 fixtures
    print("\n[4/4] 创建 fixtures...")
    fixtures = BLUECLAW / "tests" / "fixtures" / "sample_project"
    fixtures.mkdir(parents=True, exist_ok=True)
    pkg = fixtures / "package.json"
    if not pkg.exists():
        pkg.write_text('{}', encoding="utf-8")
        print(f"[OK] 创建 {pkg}")
    else:
        print(f"[OK] 已存在 {pkg}")

    # 5. 验证
    print("\n" + "=" * 60)
    print("运行自检...")
    self_check = BLUECLAW / "tests" / "self_check.py"
    if self_check.exists():
        subprocess.run([sys.executable, str(self_check)], cwd=str(ROOT))
    else:
        print(f"[WARN] 未找到自检脚本: {self_check}")

    print("\n修复完成。若仍有 Fail，按自检提示逐个处理。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
