# -*- coding: utf-8 -*-
"""
ScreenshotCapture 统一截图接口

- 抽象接口
- PlaywrightScreenshot（Web Adapter 用）
- IDEScreenshot（IDE Adapter 用）
- WebP 压缩（Pillow）
"""
from abc import ABC, abstractmethod
from typing import Optional


class ScreenshotCapture(ABC):
    """截图捕获抽象基类"""

    @abstractmethod
    async def capture(self, *args, **kwargs) -> bytes:
        """返回截图字节数据（默认 PNG 或 JPEG）"""
        ...

    def compress(self, data: bytes, quality: int = 80) -> bytes:
        """使用 Pillow 压缩为 WebP"""
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(data))
            # 转换为 RGB（去除 alpha 通道，WebP 兼容更好）
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, format="WEBP", quality=quality)
            return out.getvalue()
        except Exception:
            # 如果 Pillow 失败或输入不是图片，原样返回
            return data

    def resize(self, data: bytes, max_dimension: int = 1280) -> bytes:
        """按最大边缩放截图，减少内存占用和传输耗时"""
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(data))
            w, h = img.size
            if max(w, h) <= max_dimension:
                return data
            ratio = max_dimension / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, format="WEBP", quality=75)
            return out.getvalue()
        except Exception:
            return data

    def optimize(self, data: bytes, quality: int = 75, max_dimension: int = 1280) -> bytes:
        """组合优化：先缩放再压缩"""
        resized = self.resize(data, max_dimension)
        return self.compress(resized, quality)


class PlaywrightScreenshot(ScreenshotCapture):
    """Web 浏览器截图（当前为 mock，接口与 Playwright 对齐）"""

    async def capture(self, page=None) -> bytes:
        """page 为 Playwright Page 对象；支持真实截图"""
        if page is not None:
            try:
                return await page.screenshot(type="png")
            except Exception:
                pass
        # Fallback：返回 1x1 透明 PNG
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


class IDEScreenshot(ScreenshotCapture):
    """IDE 代码区截图（当前为 mock）"""

    async def capture(
        self,
        project_path: Optional[str] = None,
        active_file: Optional[str] = None,
        line_range: Optional[tuple] = None,
    ) -> bytes:
        """当前返回 mock 字节，表示代码区快照"""
        # Mock：返回 1x1 透明 PNG
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
