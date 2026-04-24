# -*- coding: utf-8 -*-
"""
WebExecutor - 动作执行器 + 截图闭环

- click / fill / scroll / select / navigate
- 每个动作前后强制截图
- 生成 OperationRecord 并保存检查点
- 失败重试机制
"""
import time
from typing import Optional, Dict, Any

from blueclaw.adapter.models import ExecutionStep, StepResult
from blueclaw.adapter.models import TargetDescription
from blueclaw.adapter.web.analyzer import WebAnalyzer
from blueclaw.adapter.web.distraction import DistractionDetector
from blueclaw.adapter.web.locator import WebLocator
from blueclaw.adapter.web.validator import WebValidator
from blueclaw.adapter.web.recovery import RecoveryController
from blueclaw.adapter.web.visualization import CanvasMindVisualizer
from blueclaw.adapter.web.checkpoint import WebCheckpointManager
from blueclaw.adapter.core.operation_record import OperationRecord, OperationLog
from blueclaw.adapter.core.checkpoint_v2 import CheckpointManagerV2
from blueclaw.adapter.core.screenshot import ScreenshotCapture


class WebExecutor:
    """Web 动作执行器"""

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture,
        operation_log: Optional[OperationLog] = None,
        checkpoint_manager: Optional[CheckpointManagerV2] = None,
        validator: Optional[WebValidator] = None,
        recovery_controller: Optional[RecoveryController] = None,
        visualizer: Optional[CanvasMindVisualizer] = None,
        web_checkpoint_manager: Optional[WebCheckpointManager] = None,
    ):
        self.screenshot_capture = screenshot_capture
        self.analyzer = WebAnalyzer(screenshot_capture=screenshot_capture)
        self.detector = DistractionDetector()
        self.locator = WebLocator()
        self.operation_log = operation_log
        self.checkpoint_manager = checkpoint_manager
        self.validator = validator
        self.recovery_controller = recovery_controller
        self.visualizer = visualizer
        self.web_checkpoint_manager = web_checkpoint_manager

    async def execute_step(self, step: ExecutionStep, page, blueprint_id: str = "", _skip_recovery: bool = False) -> StepResult:
        """执行单个步骤并生成完整记录（集成验证、恢复、可视化、WebCheckpoint）"""
        t0 = time.time()
        before_ss = b""
        after_ss = b""
        error_msg = None
        status = "success"
        output = ""
        located_element = None
        analysis = None

        # 可视化：注入覆盖层和进度条
        if self.visualizer:
            try:
                await self.visualizer.inject_overlay(page)
                total_steps = step.action.params.get("_total_steps", 1)
                current_step = step.action.params.get("_current_step", 1)
                await self.visualizer.show_progress(page, current_step, total_steps, 0)
            except Exception:
                pass

        try:
            # 1. 执行前截图
            before_ss = await self.screenshot_capture.capture(page)

            # 2. 执行动作
            action_type = step.action.type
            target = step.action.target or TargetDescription(semantic="")

            if action_type == "navigate":
                url = target.semantic or "about:blank"
                await page.goto(url, wait_until="networkidle", timeout=10000)
                output = f"Navigated to {page.url}"

            elif action_type == "scroll":
                dx = step.action.params.get("dx", 0)
                dy = step.action.params.get("dy", 0)
                await page.evaluate(f"() => window.scrollBy({dx}, {dy})")
                output = f"Scrolled by ({dx}, {dy})"

            elif action_type in ("click", "input", "select"):
                # 需要定位元素的动作
                analysis = await self.analyzer.analyze(page)
                # 过滤干扰元素
                distractions = self.detector.detect(
                    analysis.elements, analysis.screenshot,
                    {"width": analysis.viewport_width, "height": analysis.viewport_height}
                )
                analysis.distractions = distractions

                # 定位目标元素
                loc_result = await self.locator.locate(target, analysis.elements, page=page)
                if not loc_result.found:
                    raise RuntimeError(f"Element not found: {target.semantic or target.selector}")

                located_element = loc_result.element
                # 执行动作
                if action_type == "click":
                    if located_element and located_element.selector:
                        await page.click(located_element.selector, timeout=10000)
                    else:
                        coords = located_element.normalized_coords if located_element else {"x": 0, "y": 0}
                        vw = analysis.viewport_width or 1
                        vh = analysis.viewport_height or 1
                        await page.mouse.click(
                            int(coords.get("x", 0) * vw),
                            int(coords.get("y", 0) * vh)
                        )
                    output = f"Clicked {located_element.selector if located_element else 'coordinate'}"

                elif action_type == "input":
                    text = step.action.params.get("value", "")
                    if located_element and located_element.selector:
                        await page.fill(located_element.selector, text, timeout=10000)
                    output = f"Filled '{text}' into {located_element.selector if located_element else 'input'}"

                elif action_type == "select":
                    value = step.action.params.get("value", "")
                    if located_element and located_element.selector:
                        await page.select_option(located_element.selector, value, timeout=10000)
                    output = f"Selected '{value}'"

            elif action_type == "screenshot":
                # 纯截图步骤，after_ss 会在下面再次捕获
                output = "Screenshot captured"

            elif action_type == "wait":
                ms = step.action.params.get("ms", 1000)
                await page.wait_for_timeout(ms)
                output = f"Waited {ms}ms"

            else:
                output = f"Unsupported action: {action_type}"
                status = "failed"

            # 3. 执行后截图（强制）
            raw_after = await self.screenshot_capture.capture(page)
            after_ss = self.screenshot_capture.compress(raw_after, quality=80)

        except Exception as e:
            status = "failed"
            error_msg = str(e)
            output = error_msg
            # 失败时也要截图
            try:
                raw_after = await self.screenshot_capture.capture(page)
                after_ss = self.screenshot_capture.compress(raw_after, quality=80)
            except Exception:
                pass

        # 4. 验证（如果配置了验证规则且动作本身未失败）
        if status == "success" and step.validation and self.validator:
            try:
                val_result = await self.validator.validate(page, step.validation)
                if not val_result.success:
                    status = "failed"
                    error_msg = f"Validation failed: {val_result.message}"
                    output = error_msg
            except Exception as e:
                status = "failed"
                error_msg = f"Validation error: {e}"
                output = error_msg

        # 5. 自动恢复（如果失败且配置了恢复控制器）
        recovery_action = None
        if status == "failed" and self.recovery_controller and not _skip_recovery:
            try:
                recovery_action = await self.recovery_controller.recover(
                    page, step, error_msg or "Unknown error", blueprint_id, self
                )
                if recovery_action.action in ("retry", "fallback"):
                    status = "success"
                    error_msg = None
                    output = f"Recovered via {recovery_action.action}: {recovery_action.message}"
                elif recovery_action.action == "rollback":
                    # rollback 后需要重新执行当前步骤？简化处理：标记为需要重试
                    status = "failed"
                    output = f"Rolled back: {recovery_action.message}. Step needs re-execution."
            except Exception:
                pass

        duration_ms = (time.time() - t0) * 1000
        step_result = StepResult(
            status=status,
            output=output,
            error=error_msg,
            duration_ms=duration_ms,
            needs_intervention=(status == "failed"),
        )

        # 6. 可视化：操作标记 + 干扰高亮 + 检查点旗帜
        if self.visualizer:
            try:
                if located_element:
                    await self.visualizer.mark_operation(page, located_element, step.action.type)
                if analysis and analysis.distractions:
                    await self.visualizer.highlight_distractions(page, analysis.distractions)
            except Exception:
                pass

        # 7. 保存 WebCheckpoint（页面状态检查点）
        if self.web_checkpoint_manager:
            try:
                await self.web_checkpoint_manager.save(page, blueprint_id or step.step_id, step.step_id)
            except Exception:
                pass

        # 8. 生成 OperationRecord
        record = OperationRecord(
            record_id=f"rec_{int(time.time() * 1000)}",
            blueprint_id=blueprint_id or step.step_id,
            step_id=step.step_id,
            step_type=step.action.type,
            params=step.action.params,
            result=step_result,
            before_screenshot=before_ss or None,
            after_screenshot=after_ss or None,
            timestamp=time.time(),
            state_snapshot=await self._get_state_snapshot(page),
        )

        if self.operation_log:
            self.operation_log.append(record)
        if self.checkpoint_manager:
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.checkpoint_manager.save_from_record, record)

        return step_result

    async def execute_step_with_retry(self, step: ExecutionStep, page, max_retries: int = 1) -> StepResult:
        """带重试的执行"""
        result = await self.execute_step(step, page)
        for _ in range(max_retries):
            if result.status == "success":
                break
            # 重试前等待 500ms
            await page.wait_for_timeout(500)
            result = await self.execute_step(step, page)
        return result

    async def _get_state_snapshot(self, page) -> Dict[str, Any]:
        """获取页面状态快照"""
        try:
            cookies = await page.context.cookies()
        except Exception:
            cookies = []
        try:
            local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        except Exception:
            local_storage = "{}"
        return {
            "url": page.url,
            "title": await page.title(),
            "cookies": cookies,
            "local_storage": local_storage,
        }
