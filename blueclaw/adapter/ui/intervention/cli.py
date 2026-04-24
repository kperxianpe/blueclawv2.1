# -*- coding: utf-8 -*-
"""
CliInterventionUI - 命令行交互兜底
"""
import os
import tempfile
from datetime import datetime
from blueclaw.adapter.ui.intervention.base import InterventionUI, InterventionResult


class CliInterventionUI(InterventionUI):
    """命令行干预界面"""

    async def show(self, step, screenshot: bytes, error_info: str = None) -> InterventionResult:
        print("\n" + "=" * 50)
        print("[干预请求] 步骤执行需要确认")
        print(f"步骤名称: {getattr(step, 'name', 'unknown')}")
        if error_info:
            print(f"错误信息: {error_info}")
        print("=" * 50)

        # 将截图保存到临时文件供用户查看
        tmp_path = os.path.join(tempfile.gettempdir(), f"intervention_{datetime.now().strftime('%Y%m%d%H%M%S')}.webp")
        with open(tmp_path, "wb") as f:
            f.write(screenshot)
        print(f"截图已保存: {tmp_path}")

        print("\n可选操作:")
        print("  1) retry   - 重试当前步骤")
        print("  2) skip    - 跳过当前步骤")
        print("  3) replan  - 重新规划")
        print("  4) abort   - 中止任务")

        # 由于命令行交互在异步环境中可能有阻塞风险，这里模拟默认选择 retry
        # 实际生产环境可改用 aioconsole 或从外部文件读取输入
        choice = input("请输入选择 (retry/skip/replan/abort): ").strip().lower()
        if choice not in ("retry", "skip", "replan", "abort"):
            choice = "retry"

        text = input("请输入补充说明（可选）: ").strip() or None

        return InterventionResult(
            type="button",
            choice=choice,
            text=text,
        )
