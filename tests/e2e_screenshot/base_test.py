#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw v2.5 截图对比测试基类
支持：截图保存、像素级对比、差异高亮、测试报告生成
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageChops

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 截图保存根目录
SCREENSHOT_ROOT = Path(__file__).parent / "screenshots"
REPORT_ROOT = Path(__file__).parent / "reports"


class ScreenshotStep:
    """单步截图记录"""
    def __init__(self, step_idx: int, desc: str, filepath: Path):
        self.step_idx = step_idx
        self.desc = desc
        self.filepath = filepath
        self.diff_score: float = 0.0  # 0.0 = 完全相同, 1.0 = 完全不同
        self.diff_path: Optional[Path] = None
        self.passed: bool = True
        self.notes: str = ""


class ScreenshotTestBase:
    """
    截图对比测试基类
    用法:
        async def test_something(self, page, backend):
            t = ScreenshotTestBase(page, "TB-001")
            await t.start()
            await t.screenshot("初始状态")
            await t.click("[data-testid='send-btn']")
            await t.screenshot("点击后")
            await t.finish()
    """

    def __init__(self, page, test_id: str):
        self.page = page
        self.test_id = test_id.upper()
        self.steps: List[ScreenshotStep] = []
        self.step_counter = 0
        self.start_time = 0.0
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.test_dir = SCREENSHOT_ROOT / self.test_id
        self.test_dir.mkdir(parents=True, exist_ok=True)
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    async def start(self):
        """测试开始，打开前端页面"""
        self.start_time = time.time()
        print(f"\n{'='*60}")
        print(f"[TEST START] {self.test_id}")
        print(f"{'='*60}")
        # 打开前端页面
        await self.page.goto("http://localhost:5173")
        await self.page.wait_for_load_state("networkidle")
        # 等待 React 渲染完成（通过检查关键元素）
        try:
            await self.page.wait_for_selector("text=Blueclaw", timeout=5000)
        except Exception:
            pass
        await asyncio.sleep(1)

    async def screenshot(self, desc: str, wait_ms: int = 500) -> Path:
        """
        截图并保存
        :param desc: 截图描述（用于文件名和报告）
        :param wait_ms: 截图前等待时间（让动画完成）
        :return: 截图文件路径
        """
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000)

        self.step_counter += 1
        ts = datetime.now().strftime("%H%M%S")
        safe_desc = desc.replace(" ", "_").replace("/", "_")[:30]
        filename = f"{self.test_id}_S{self.step_counter}_{safe_desc}_{ts}.png"
        filepath = self.test_dir / filename

        await self.page.screenshot(path=str(filepath), full_page=False)
        step = ScreenshotStep(self.step_counter, desc, filepath)
        self.steps.append(step)

        prev = self.steps[-2] if len(self.steps) >= 2 else None
        if prev:
            diff_score, diff_path = self._compare_images(prev.filepath, filepath)
            step.diff_score = diff_score
            step.diff_path = diff_path
            step.passed = diff_score > 0.001  # 有可见差异
            if not step.passed:
                step.notes = f"与 S{prev.step_idx} 无可见差异（score={diff_score:.6f}）"
                print(f"  [WARN] S{self.step_counter} vs S{prev.step_idx}: 无可见差异")
            else:
                print(f"  [OK] S{self.step_counter} vs S{prev.step_idx}: diff={diff_score:.4f}")
        else:
            print(f"  [OK] S{self.step_counter} (基准截图)")

        return filepath

    async def click(self, selector: str, force: bool = False):
        """点击元素"""
        print(f"  [ACTION] click: {selector}")
        await self.page.click(selector, force=force)
        await asyncio.sleep(0.3)

    async def type_text(self, selector: str, text: str):
        """输入文字"""
        print(f"  [ACTION] type: {selector} = {text[:30]}...")
        await self.page.fill(selector, text)
        await asyncio.sleep(0.2)

    async def wait_for(self, selector: str, timeout: int = 10000, state: str = "visible"):
        """等待元素出现"""
        print(f"  [WAIT] {selector} (timeout={timeout}ms)")
        await self.page.wait_for_selector(selector, timeout=timeout, state=state)

    async def wait_for_text(self, text: str, timeout: int = 10000):
        """等待文字出现"""
        print(f"  [WAIT] text='{text}' (timeout={timeout}ms)")
        await self.page.wait_for_selector(f"text={text}", timeout=timeout)

    async def hover(self, selector: str):
        """鼠标悬停"""
        print(f"  [ACTION] hover: {selector}")
        await self.page.hover(selector)
        await asyncio.sleep(0.5)

    async def scroll_to(self, selector: str):
        """滚动到元素"""
        el = await self.page.query_selector(selector)
        if el:
            await el.scroll_into_view_if_needed()

    def _compare_images(self, path1: Path, path2: Path) -> Tuple[float, Optional[Path]]:
        """
        像素级对比两张截图
        :return: (差异分数 0.0~1.0, 差异图路径或None)
        """
        try:
            img1 = Image.open(path1).convert("RGB")
            img2 = Image.open(path2).convert("RGB")

            # 统一尺寸
            if img1.size != img2.size:
                img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)

            diff = ImageChops.difference(img1, img2)
            bbox = diff.getbbox()

            if bbox is None:
                return 0.0, None

            # 计算差异分数
            diff_data = list(diff.getdata())
            total_pixels = len(diff_data)
            diff_pixels = sum(1 for r, g, b in diff_data if r > 5 or g > 5 or b > 5)
            score = diff_pixels / total_pixels if total_pixels > 0 else 0.0

            # 生成差异高亮图
            diff_highlight = diff.point(lambda p: p * 5 if p > 10 else 0)
            diff_filename = f"{path1.stem}_vs_{path2.stem}_diff.png"
            diff_path = self.test_dir / diff_filename
            diff_highlight.save(diff_path)

            return score, diff_path
        except Exception as e:
            print(f"  [ERROR] 截图对比失败: {e}")
            return 0.0, None

    async def finish(self) -> bool:
        """测试结束，生成报告"""
        elapsed = time.time() - self.start_time
        passed = all(s.passed for s in self.steps[1:])  # S0 是基准，不需要对比
        report_path = self._generate_report(elapsed)

        print(f"\n{'='*60}")
        status = "PASSED" if passed else "FAILED"
        print(f"[TEST {status}] {self.test_id} | 步骤:{len(self.steps)} | 耗时:{elapsed:.1f}s")
        print(f"[REPORT] {report_path}")
        print(f"{'='*60}")
        return passed

    def _generate_report(self, elapsed: float) -> Path:
        """生成 Markdown 测试报告"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = REPORT_ROOT / f"{self.test_id}_report_{ts}.md"

        lines = [
            f"# 测试报告: {self.test_id}",
            "",
            "### 环境信息",
            f"- 日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- 耗时: {elapsed:.1f}s",
            f"- 步骤数: {len(self.steps)}",
            "",
            "### 截图清单",
            "| 步骤 | 文件名 | 描述 | 差异分数 | 结果 |",
            "|------|--------|------|----------|------|",
        ]

        for s in self.steps:
            diff_str = f"{s.diff_score:.6f}" if s.step_idx > 1 else "基准"
            result = "✅" if s.passed else "❌"
            if s.step_idx == 1:
                result = "📍"
            rel_path = s.filepath.relative_to(Path(__file__).parent)
            lines.append(
                f"| S{s.step_idx} | `{s.filepath.name}` | {s.desc} | {diff_str} | {result} |"
            )

        # 失败记录
        failures = [s for s in self.steps if not s.passed and s.step_idx > 1]
        if failures:
            lines.extend(["", "### 失败记录", ""])
            for s in failures:
                lines.extend([
                    f"**步骤**: S{s.step_idx} ({s.desc})",
                    f"**预期差异**: 操作后有可见变化",
                    f"**实际**: {s.notes}",
                    f"**诊断**: 截图对比无可见差异，可能原因：前端未响应 / 后端未处理 / WebSocket 未广播",
                    f"**修复**: 检查对应链路的事件绑定和状态更新",
                    "",
                ])
        else:
            lines.extend(["", "### 结果", "- ✅ 全部截图均有预期差异 → **通过**"])

        lines.extend([
            "",
            "### 截图预览",
            "",
        ])
        for s in self.steps:
            rel = s.filepath.relative_to(Path(__file__).parent).as_posix()
            lines.append(f"#### S{s.step_idx}: {s.desc}")
            lines.append(f"![S{s.step_idx}]({rel})")
            if s.diff_path:
                diff_rel = s.diff_path.relative_to(Path(__file__).parent).as_posix()
                lines.append(f"![diff]({diff_rel})")
            lines.append("")

        report_file.write_text("\n".join(lines), encoding="utf-8")
        return report_file


async def wait_for_backend(timeout: int = 30) -> bool:
    """检查后端是否就绪"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen("http://localhost:8006", timeout=2)
            return True
        except Exception:
            await asyncio.sleep(1)
    return False
