# -*- coding: utf-8 -*-
"""
WebAnalyzer - 页面结构分析器

- DOM 提取
- 可交互元素识别
- bounding box 计算
- 截图坐标映射（归一化 0-1）
"""
import time
from typing import List, Dict, Any, Optional

from blueclaw.adapter.web.models import WebElement, PageAnalysis
from blueclaw.adapter.core.screenshot import ScreenshotCapture


# JavaScript 提取脚本
_EXTRACT_SCRIPT = """
() => {
    const selectors = [
        'button', 'input', 'a', 'select', 'textarea',
        '[role="button"]', '[role="link"]', '[contenteditable="true"]',
        'div'
    ];
    const seen = new Set();
    const results = [];

    selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            if (seen.has(el)) return;
            seen.add(el);

            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);

            // 过滤不可见元素
            if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) < 0.1) return;
            if (rect.width === 0 || rect.height === 0) return;

            const tag = el.tagName.toLowerCase();
            // 对 div 进行额外过滤：只保留有标识或特殊定位的，避免提取无意义容器
            if (tag === 'div') {
                const hasIdentity = el.id || el.className || el.getAttribute('role');
                const isSpecialPosition = style.position === 'fixed' || style.position === 'sticky';
                if (!hasIdentity && !isSpecialPosition) return;
            }

            // 生成简单 CSS selector
            let idPart = el.id ? '#' + el.id : '';
            let classes = Array.from(el.classList).slice(0, 2).map(c => '.' + c).join('');
            let simpleSelector = tag + idPart + classes;

            // 生成简单 XPath
            let idx = 1;
            let sibling = el.previousElementSibling;
            while (sibling) {
                if (sibling.tagName === el.tagName) idx++;
                sibling = sibling.previousElementSibling;
            }
            let xpath = '//' + tag + '[' + idx + ']';

            results.push({
                tag: tag,
                type: el.type || '',
                text: (el.innerText || '').trim().substring(0, 200),
                aria_label: el.getAttribute('aria-label') || '',
                placeholder: el.getAttribute('placeholder') || '',
                title: el.getAttribute('title') || '',
                selector: simpleSelector,
                xpath: xpath,
                bbox: {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                },
                z_index: parseInt(style.zIndex, 10) || 0,
                position: style.position,
                attributes: {
                    id: el.id || '',
                    className: el.className || '',
                    name: el.getAttribute('name') || '',
                    href: el.getAttribute('href') || '',
                    role: el.getAttribute('role') || ''
                }
            });
        });
    });
    return results;
}
"""


class WebAnalyzer:
    """页面结构分析器"""

    def __init__(self, screenshot_capture: Optional[ScreenshotCapture] = None):
        self.screenshot_capture = screenshot_capture

    async def analyze(self, page) -> PageAnalysis:
        """分析页面并返回 PageAnalysis"""
        t0 = time.time()

        # 1. 截图
        screenshot = b""
        if self.screenshot_capture:
            screenshot = await self.screenshot_capture.capture(page)

        # 2. 获取 viewport 和页面基本信息
        viewport = await page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
        url = page.url
        title = await page.title()

        # 3. 提取可交互元素
        raw_elements = await page.evaluate(_EXTRACT_SCRIPT)
        elements = [self._to_web_element(r, viewport) for r in raw_elements]

        # 按面积排序，通常大元素更重要
        elements.sort(key=lambda e: e.bbox.get("width", 0) * e.bbox.get("height", 0), reverse=True)

        return PageAnalysis(
            url=url,
            title=title,
            timestamp=time.time(),
            screenshot=screenshot,
            elements=elements,
            viewport_width=viewport.get("width", 0),
            viewport_height=viewport.get("height", 0),
        )

    def _to_web_element(self, raw: Dict[str, Any], viewport: Dict[str, int]) -> WebElement:
        bbox = raw.get("bbox", {})
        vw = viewport.get("width", 1)
        vh = viewport.get("height", 1)
        tag = raw.get("tag", "")
        elem_type = self._infer_element_type(tag, raw.get("type", ""), raw.get("attributes", {}))

        return WebElement(
            id=raw.get("attributes", {}).get("id", "") or f"{tag}_{int(bbox.get('x', 0))}_{int(bbox.get('y', 0))}",
            tag=tag,
            element_type=elem_type,
            text=raw.get("text", ""),
            aria_label=raw.get("aria_label", ""),
            placeholder=raw.get("placeholder", ""),
            title=raw.get("title", ""),
            selector=raw.get("selector", ""),
            xpath=raw.get("xpath", ""),
            bbox=bbox,
            normalized_coords={
                "x": max(0.0, min(1.0, bbox.get("x", 0) / vw)),
                "y": max(0.0, min(1.0, bbox.get("y", 0) / vh)),
                "width": max(0.0, min(1.0, bbox.get("width", 0) / vw)),
                "height": max(0.0, min(1.0, bbox.get("height", 0) / vh)),
            },
            z_index=raw.get("z_index", 0),
            position=raw.get("position", ""),
            attributes=raw.get("attributes", {}),
        )

    @staticmethod
    def _infer_element_type(tag: str, input_type: str, attrs: Dict[str, Any]) -> str:
        role = attrs.get("role", "")
        if tag == "button" or role == "button" or tag == "input" and input_type in ("submit", "button", "reset"):
            return "button"
        if tag == "input" or tag == "textarea":
            return "input"
        if tag == "a" or role == "link":
            return "link"
        if tag == "select":
            return "select"
        if attrs.get("contenteditable") == "true":
            return "textarea"
        return "other"
