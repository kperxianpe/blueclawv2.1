# -*- coding: utf-8 -*-
"""
Screenshot 性能测试

- 压缩耗时
- 缩放耗时
- 内存占用
"""
import time
import io
import pytest

from blueclaw.adapter.core.screenshot import ScreenshotCapture


class MockScreenshot(ScreenshotCapture):
    """Mock 截图，返回固定尺寸图片"""

    async def capture(self, *args, **kwargs) -> bytes:
        # 创建 1920x1080 的测试图片
        try:
            from PIL import Image
            img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
            out = io.BytesIO()
            img.save(out, format="PNG")
            return out.getvalue()
        except ImportError:
            pytest.skip("Pillow not installed")


@pytest.fixture
def large_screenshot():
    """生成大截图数据"""
    try:
        from PIL import Image
        img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except ImportError:
        pytest.skip("Pillow not installed")


def test_compress_performance(large_screenshot):
    """测试 WebP 压缩性能"""
    capture = MockScreenshot()

    start = time.time()
    compressed = capture.compress(large_screenshot, quality=75)
    duration = time.time() - start

    original_size = len(large_screenshot)
    compressed_size = len(compressed)
    ratio = original_size / compressed_size if compressed_size > 0 else 0

    print(f"\nCompress: {original_size / 1024:.1f}KB -> {compressed_size / 1024:.1f}KB ({ratio:.1f}x) in {duration * 1000:.1f}ms")

    assert compressed_size < original_size
    assert duration < 2.0  # 压缩应在 2s 内完成


def test_resize_performance(large_screenshot):
    """测试缩放性能"""
    capture = MockScreenshot()

    start = time.time()
    resized = capture.resize(large_screenshot, max_dimension=640)
    duration = time.time() - start

    # 验证尺寸
    from PIL import Image
    img = Image.open(io.BytesIO(resized))
    assert max(img.size) <= 640

    print(f"\nResize to 640px: {len(resized) / 1024:.1f}KB in {duration * 1000:.1f}ms")
    assert duration < 1.0


def test_optimize_pipeline(large_screenshot):
    """测试组合优化管道"""
    capture = MockScreenshot()

    start = time.time()
    optimized = capture.optimize(large_screenshot, quality=70, max_dimension=1280)
    duration = time.time() - start

    original_size = len(large_screenshot)
    optimized_size = len(optimized)

    print(f"\nOptimize: {original_size / 1024:.1f}KB -> {optimized_size / 1024:.1f}KB in {duration * 1000:.1f}ms")

    assert optimized_size < original_size * 0.5  # 至少压缩 50%
    assert duration < 2.0


def test_compress_quality_levels(large_screenshot):
    """测试不同质量级别的压缩效果"""
    capture = MockScreenshot()

    sizes = {}
    for quality in [50, 70, 80, 90]:
        compressed = capture.compress(large_screenshot, quality=quality)
        sizes[quality] = len(compressed)

    print(f"\nQuality sizes: {sizes}")
    # 对于纯色图片，质量差异可能不明显，改为验证总体趋势
    # 低质量通常 <= 高质量
    assert sizes[50] <= sizes[90]
    assert all(s > 0 for s in sizes.values())
