# -*- coding: utf-8 -*-
"""
WebValidator - 页面状态验证器

支持：
- url_match: URL 正则匹配
- presence: 元素存在性（Playwright locator）
- text_contains: 文本内容包含验证
- visual_match: 截图视觉对比（SSIM）
- custom: 自定义验证函数
- return_code: HTTP 状态码（Web 上下文占位）
"""
import re
import os
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

from blueclaw.adapter.models import ValidationRule
from blueclaw.adapter.core.screenshot import ScreenshotCapture


class ValidationResult(BaseModel):
    """验证结果"""
    success: bool = False
    type: str = ""
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


def _compute_ssim(img1_bytes: bytes, img2_bytes: bytes) -> float:
    """使用 OpenCV + NumPy 计算 SSIM（简化版，不依赖 scikit-image）"""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return 0.0

    nparr1 = np.frombuffer(img1_bytes, np.uint8)
    nparr2 = np.frombuffer(img2_bytes, np.uint8)
    img1 = cv2.imdecode(nparr1, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imdecode(nparr2, cv2.IMREAD_GRAYSCALE)

    if img1 is None or img2 is None:
        return 0.0

    # 统一尺寸
    if img1.shape != img2.shape:
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (w, h))
        img2 = cv2.resize(img2, (w, h))

    # SSIM 常量
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)

    mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(img1 ** 2, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img2 ** 2, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / (
        (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
    )
    return float(ssim_map.mean())


class WebValidator:
    """Web 页面状态验证器"""

    def __init__(
        self,
        screenshot_capture: Optional[ScreenshotCapture] = None,
        timeout: int = 10,
    ):
        self.screenshot_capture = screenshot_capture
        self.timeout = timeout
        self._custom_registry: Dict[str, Callable] = {}

    def register_custom(self, name: str, fn: Callable) -> None:
        """注册自定义验证函数"""
        self._custom_registry[name] = fn

    async def validate(
        self,
        page,
        rule: ValidationRule,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """根据验证规则验证页面状态"""
        vtype = rule.type
        expected = rule.expected
        ctx = context or {}

        try:
            if vtype == "url_match":
                return await self._validate_url(page, expected)
            elif vtype == "presence":
                return await self._validate_presence(page, expected)
            elif vtype == "text_contains":
                return await self._validate_text_contains(page, expected)
            elif vtype == "visual_match":
                return await self._validate_visual(page, expected, ctx)
            elif vtype == "custom":
                return await self._validate_custom(page, expected)
            elif vtype == "return_code":
                return ValidationResult(
                    success=True,
                    type="return_code",
                    message="return_code validation is not applicable in Web context",
                )
            else:
                return ValidationResult(
                    success=False,
                    type=vtype,
                    message=f"Unknown validation type: {vtype}",
                )
        except Exception as e:
            return ValidationResult(
                success=False,
                type=vtype,
                message=f"Validation error: {e}",
                details={"error": str(e)},
            )

    async def _validate_url(self, page, expected: Any) -> ValidationResult:
        pattern = expected if isinstance(expected, str) else str(expected)
        current_url = page.url
        matched = bool(re.search(pattern, current_url))
        return ValidationResult(
            success=matched,
            type="url_match",
            message=f"URL '{current_url}' {'matches' if matched else 'does not match'} pattern '{pattern}'",
            details={"url": current_url, "pattern": pattern},
        )

    async def _validate_presence(self, page, expected: Any) -> ValidationResult:
        if isinstance(expected, bool):
            if expected:
                return ValidationResult(
                    success=True, type="presence",
                    message="Presence check passed (expected=True)",
                )
            return ValidationResult(
                success=False, type="presence",
                message="Presence check failed (expected=False)",
            )
        selector = expected if isinstance(expected, str) else expected.get("selector", "")
        try:
            count = await page.locator(selector).count()
            found = count > 0
            return ValidationResult(
                success=found,
                type="presence",
                message=f"Element '{selector}' {'found' if found else 'not found'} ({count} match(es))",
                details={"selector": selector, "count": count},
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                type="presence",
                message=f"Presence check failed for '{selector}': {e}",
                details={"selector": selector, "error": str(e)},
            )

    async def _validate_text_contains(self, page, expected: Any) -> ValidationResult:
        if isinstance(expected, dict):
            selector = expected.get("selector", "")
            text = expected.get("text", "")
        else:
            selector = ""
            text = str(expected)

        try:
            if selector:
                elem_text = await page.locator(selector).first.inner_text(timeout=self.timeout * 1000)
            else:
                elem_text = await page.inner_text("body", timeout=self.timeout * 1000)
            contains = text in elem_text
            return ValidationResult(
                success=contains,
                type="text_contains",
                message=f"Text '{text}' {'found' if contains else 'not found'} in element",
                details={
                    "selector": selector,
                    "expected_text": text,
                    "actual_text": elem_text[:500],
                },
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                type="text_contains",
                message=f"Text check failed: {e}",
                details={"selector": selector, "expected_text": text, "error": str(e)},
            )

    async def _validate_visual(
        self,
        page,
        expected: Any,
        context: Dict[str, Any],
    ) -> ValidationResult:
        """视觉匹配：expected 可以是截图 bytes、文件路径，或 context 中的 baseline_screenshot"""
        baseline_bytes = b""
        if isinstance(expected, bytes):
            baseline_bytes = expected
        elif isinstance(expected, str) and os.path.exists(expected):
            with open(expected, "rb") as f:
                baseline_bytes = f.read()
        elif "baseline_screenshot" in context:
            baseline = context["baseline_screenshot"]
            baseline_bytes = baseline if isinstance(baseline, bytes) else b""

        if not baseline_bytes:
            return ValidationResult(
                success=False,
                type="visual_match",
                message="No baseline screenshot provided for visual_match",
            )

        if self.screenshot_capture is None:
            return ValidationResult(
                success=False,
                type="visual_match",
                message="screenshot_capture not configured",
            )

        try:
            current_bytes = await self.screenshot_capture.capture(page)
            if not current_bytes:
                return ValidationResult(
                    success=False,
                    type="visual_match",
                    message="Failed to capture current screenshot",
                )
            ssim = _compute_ssim(baseline_bytes, current_bytes)
            threshold = context.get("ssim_threshold", 0.8)
            matched = ssim >= threshold
            return ValidationResult(
                success=matched,
                type="visual_match",
                message=f"SSIM={ssim:.4f} (threshold={threshold}) -> {'match' if matched else 'mismatch'}",
                details={"ssim": ssim, "threshold": threshold},
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                type="visual_match",
                message=f"Visual match error: {e}",
                details={"error": str(e)},
            )

    async def _validate_custom(self, page, expected: Any) -> ValidationResult:
        fn = None
        if callable(expected):
            fn = expected
        elif isinstance(expected, str) and expected in self._custom_registry:
            fn = self._custom_registry[expected]

        if fn is None:
            return ValidationResult(
                success=False,
                type="custom",
                message=f"Custom validator not found: {expected}",
            )

        try:
            # 支持同步和异步函数
            import asyncio
            if asyncio.iscoroutinefunction(fn):
                result = await fn(page)
            else:
                result = fn(page)
                if asyncio.iscoroutine(result):
                    result = await result
            success = bool(result)
            return ValidationResult(
                success=success,
                type="custom",
                message=f"Custom validator returned {success}",
                details={"result": result},
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                type="custom",
                message=f"Custom validator error: {e}",
                details={"error": str(e)},
            )
