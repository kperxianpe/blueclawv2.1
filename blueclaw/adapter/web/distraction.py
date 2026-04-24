# -*- coding: utf-8 -*-
"""
DistractionDetector - 干扰元素检测器

- DOM 规则引擎
- 位置启发式（fixed/sticky, z-index）
- 基于截图的轻量视觉验证（Pillow）
"""
import io
from typing import List, Dict, Any

from blueclaw.adapter.web.models import WebElement


# 干扰关键词（中英文）
_DISTRACTION_KEYWORDS = [
    "ad", "ads", "advert", "promo", "promotion", "popup", "pop-up",
    "banner", "subscribe", "newsletter", "cookie", "gdpr", "modal",
    "overlay", "sponsored",
    "广告", "推广", "弹窗", "订阅", "邮件", "cookie",
]


class DistractionDetector:
    """干扰检测器"""

    def __init__(self, variance_threshold: float = 5.0):
        self.variance_threshold = variance_threshold

    def detect(
        self,
        elements: List[WebElement],
        screenshot: bytes,
        viewport_size: Dict[str, int],
    ) -> List[WebElement]:
        """检测并标记干扰元素"""
        distractions = []
        for elem in elements:
            if self._is_distraction_by_dom(elem):
                if self._is_visible_in_screenshot(elem, screenshot, viewport_size):
                    elem.is_distraction = True
                    distractions.append(elem)
        return distractions

    def _is_distraction_by_dom(self, elem: WebElement) -> bool:
        """DOM 规则判断"""
        # 关键词检查
        combined_text = " ".join([
            elem.text.lower(),
            elem.aria_label.lower(),
            elem.title.lower(),
            elem.attributes.get("className", "").lower(),
            elem.attributes.get("id", "").lower(),
        ])
        for kw in _DISTRACTION_KEYWORDS:
            if kw in combined_text:
                return True

        # 位置启发式
        if elem.position in ("fixed", "sticky"):
            return True
        if elem.z_index > 1000:
            return True

        return False

    def _is_visible_in_screenshot(
        self,
        elem: WebElement,
        screenshot: bytes,
        viewport_size: Dict[str, int],
    ) -> bool:
        """通过截图验证可见性（轻量 CV：裁剪区域后计算像素方差）"""
        try:
            from PIL import Image, ImageStat
            img = Image.open(io.BytesIO(screenshot))
            # 计算元素在截图中的像素坐标
            nw = elem.normalized_coords
            vw = viewport_size.get("width", img.width)
            vh = viewport_size.get("height", img.height)

            left = int(nw.get("x", 0) * vw)
            top = int(nw.get("y", 0) * vh)
            right = left + int(nw.get("width", 0) * vw)
            bottom = top + int(nw.get("height", 0) * vh)

            if right <= left or bottom <= top:
                return False

            # 确保在图片范围内
            left = max(0, left)
            top = max(0, top)
            right = min(img.width, right)
            bottom = min(img.height, bottom)

            cropped = img.crop((left, top, right, bottom))
            stat = ImageStat.Stat(cropped)
            # 计算 RGB 平均标准差作为方差代理
            stds = stat.stddev
            variance = sum(stds) / len(stds) if stds else 0.0
            return variance > self.variance_threshold
        except Exception:
            # Pillow 不可用或处理失败时，默认认为可见（保守策略）
            return True
