# -*- coding: utf-8 -*-
"""
Web 执行适配器（Week 24 真实 Playwright 版）

- 接入真实 Playwright Browser / Page
- 使用 WebExecutor 执行步骤（含分析/过滤/定位/截图闭环）
- 返回 WebExecutionResult
"""
import time
from typing import Dict, Any

from blueclaw.adapter.adapters.base import BaseAdapter
from blueclaw.adapter.models import (
    ExecutionBlueprint, WebExecutionResult, StepResult,
)
from blueclaw.adapter.core.operation_record import OperationLog
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2
from blueclaw.adapter.core.replan_engine import AdapterReplanEngine
from blueclaw.adapter.ui.intervention.cli import CliInterventionUI
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.web.checkpoint import WebCheckpointManager
from blueclaw.adapter.web.validator import WebValidator
from blueclaw.adapter.web.recovery import RecoveryController
from blueclaw.adapter.web.visualization import CanvasMindVisualizer


class WebAdapter(BaseAdapter):
    """Web 浏览器适配器"""

    type = "web"

    def __init__(self, headless: bool = True):
        super().__init__(
            screenshot_capture=PlaywrightScreenshot(),
            checkpoint_manager=CheckpointManagerV2(),
            intervention_ui=CliInterventionUI(),
            replan_engine=AdapterReplanEngine(),
        )
        self._headless = headless
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._current_blueprint_id = ""
        self._web_checkpoint_manager = WebCheckpointManager()
        self._validator = WebValidator(screenshot_capture=self.screenshot_capture)
        self._recovery = RecoveryController(web_checkpoint_manager=self._web_checkpoint_manager)
        self._visualizer = CanvasMindVisualizer()
        self._executor = WebExecutor(
            screenshot_capture=self.screenshot_capture,
            operation_log=None,  # 由 BaseAdapter.execute 临时创建
            checkpoint_manager=self.checkpoint_manager,
            validator=self._validator,
            recovery_controller=self._recovery,
            visualizer=self._visualizer,
            web_checkpoint_manager=self._web_checkpoint_manager,
        )

    async def init(self, blueprint: ExecutionBlueprint) -> None:
        """初始化 Playwright 浏览器环境"""
        from playwright.async_api import async_playwright
        self._current_blueprint_id = blueprint.task_id
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        viewport = blueprint.config.extra.get("viewport", {"width": 1280, "height": 720})
        self._context = await self._browser.new_context(viewport=viewport)
        self._page = await self._context.new_page()

    async def _execute_step(self, step, operation_log=None) -> StepResult:
        """通过 WebExecutor 执行步骤"""
        if self._page is None:
            raise RuntimeError("WebAdapter not initialized. Call init() first.")
        if operation_log is not None:
            self._executor.operation_log = operation_log
        return await self._executor.execute_step(step, self._page, blueprint_id=self._current_blueprint_id)

    async def _capture_screenshot(self) -> bytes:
        if self._page is None:
            return b""
        return await self.screenshot_capture.capture(self._page)

    def _get_state_snapshot(self, blueprint, current_index: int) -> Dict[str, Any]:
        url = self._page.url if self._page else ""
        title = ""
        session_storage = "{}"
        if self._page:
            import asyncio
            try:
                title = asyncio.get_event_loop().run_until_complete(self._page.title())
                session_storage = asyncio.get_event_loop().run_until_complete(
                    self._page.evaluate("() => JSON.stringify(sessionStorage)")
                )
            except Exception:
                pass
        return {
            "adapter_type": "web",
            "url": url,
            "title": title,
            "current_step_index": current_index,
            "remaining_steps": [s.model_dump() for s in blueprint.steps],
            "config": blueprint.config.model_dump(),
            "session_storage": session_storage,
        }

    def _build_partial_result(
        self, operation_log: OperationLog, blueprint, status: str, error=None
    ):
        total_ms = sum(r.result.duration_ms for r in operation_log.records)
        return WebExecutionResult(
            success=(status == "completed"),
            duration_ms=total_ms,
            output=f"Web execution {status}, records={len(operation_log.records)}",
            screenshot=None,
            error_context={"error": error, "status": status} if error else None,
        )

    async def pause(self) -> None:
        self._paused = True

    async def resume(self) -> None:
        self._paused = False

    async def cleanup(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None
        self._context = None
