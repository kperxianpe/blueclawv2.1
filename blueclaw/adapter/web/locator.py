# -*- coding: utf-8 -*-
"""
WebLocator - 目标元素定位器

- 语义匹配
- CSS Selector / XPath 生成
- 多策略降级
- 定位失败时自动截图记录上下文
"""
import difflib
from typing import List, Optional, Dict, Any

from blueclaw.adapter.web.models import WebElement, LocationResult
from blueclaw.adapter.models import TargetDescription


class WebLocator:
    """Web 元素定位器"""

    async def locate(
        self,
        target: TargetDescription,
        elements: List[WebElement],
        page=None,
    ) -> LocationResult:
        """定位目标元素"""
        # 策略 1: semantic 文本匹配
        if target and target.semantic:
            match = self._locate_by_semantic(target.semantic, elements)
            if match:
                return LocationResult(found=True, strategy="semantic", element=match)

        # 策略 2: selector 直接匹配
        if target and target.selector:
            match = await self._locate_by_selector(target.selector, elements, page)
            if match:
                return LocationResult(found=True, strategy="selector", element=match)

        # 策略 3: coordinate 坐标降级
        if target and target.coordinates:
            match = self._locate_by_coordinate(target.coordinates, elements)
            if match:
                return LocationResult(found=True, strategy="coordinate", element=match)

        return LocationResult(
            found=False,
            strategy="fallback",
            fallback_reason="All location strategies failed",
        )

    def _locate_by_semantic(self, semantic: str, elements: List[WebElement]) -> Optional[WebElement]:
        """基于文本语义匹配"""
        query = semantic.lower().strip()
        candidates = []
        for elem in elements:
            if not elem.is_visible or elem.is_distraction:
                continue
            texts = [
                elem.text.lower(),
                elem.aria_label.lower(),
                elem.placeholder.lower(),
                elem.title.lower(),
                elem.attributes.get("name", "").lower(),
            ]
            best_score = 0.0
            for t in texts:
                if not t:
                    continue
                if query in t:
                    score = len(query) / len(t) if t else 0.0
                else:
                    score = difflib.SequenceMatcher(None, query, t).ratio()
                if score > best_score:
                    best_score = score
            if best_score > 0.3:
                candidates.append((elem, best_score))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    async def _locate_by_selector(
        self,
        selector: str,
        elements: List[WebElement],
        page=None,
    ) -> Optional[WebElement]:
        """基于 CSS Selector 匹配"""
        # 优先在已有 elements 中查找 selector 包含关系
        for elem in elements:
            if elem.selector == selector or selector in elem.selector:
                return elem
        # 若有 page，尝试用 page.locator 验证（但无法直接映射回 WebElement）
        if page is not None:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    # 回退：返回一个占位 WebElement
                    return WebElement(id="selector_match", tag="unknown", selector=selector)
            except Exception:
                pass
        return None

    def _locate_by_coordinate(
        self,
        coordinates: Dict[str, int],
        elements: List[WebElement],
    ) -> Optional[WebElement]:
        """基于坐标找最近元素"""
        tx = coordinates.get("x", 0)
        ty = coordinates.get("y", 0)
        best = None
        best_dist = float("inf")
        for elem in elements:
            if not elem.is_visible or elem.is_distraction:
                continue
            cx = elem.bbox.get("x", 0) + elem.bbox.get("width", 0) / 2
            cy = elem.bbox.get("y", 0) + elem.bbox.get("height", 0) / 2
            dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = elem
        return best
