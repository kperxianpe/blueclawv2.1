# -*- coding: utf-8 -*-
"""
Debug Mode - 调试模式控制器

- 详细日志输出控制
- 性能计时装饰器
- 内存使用监控
- 调用追踪
"""
import functools
import time
import tracemalloc
import logging
from typing import Optional, Callable, Any
from contextlib import contextmanager


logger = logging.getLogger("blueclaw.adapter.debug")


class DebugMode:
    """调试模式控制器（单例）"""

    _instance: Optional["DebugMode"] = None

    def __new__(cls) -> "DebugMode":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._log_level = logging.DEBUG
            cls._instance._trace_memory = False
        return cls._instance

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self, trace_memory: bool = False) -> None:
        """启用调试模式"""
        self._enabled = True
        self._trace_memory = trace_memory
        logging.basicConfig(level=self._log_level, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        if trace_memory:
            tracemalloc.start()
            logger.info("Memory tracing enabled")
        logger.info("Debug mode enabled")

    def disable(self) -> None:
        """禁用调试模式"""
        self._enabled = False
        if self._trace_memory:
            tracemalloc.stop()
        logger.info("Debug mode disabled")

    def log(self, message: str, level: int = logging.DEBUG) -> None:
        """条件日志输出"""
        if self._enabled:
            logger.log(level, message)

    def get_memory_snapshot(self) -> Optional[str]:
        """获取内存快照（如果启用了内存追踪）"""
        if not self._trace_memory:
            return None
        current, peak = tracemalloc.get_traced_memory()
        return f"Current: {current / 1024 / 1024:.2f}MB, Peak: {peak / 1024 / 1024:.2f}MB"


def timed(func: Callable) -> Callable:
    """装饰器：记录函数执行耗时"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        debug = DebugMode()
        if not debug.enabled:
            return await func(*args, **kwargs)
        start = time.time()
        debug.log(f"[TIMED] Enter {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = (time.time() - start) * 1000
            debug.log(f"[TIMED] Exit {func.__name__} ({elapsed:.1f}ms)")

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        debug = DebugMode()
        if not debug.enabled:
            return func(*args, **kwargs)
        start = time.time()
        debug.log(f"[TIMED] Enter {func.__name__}")
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = (time.time() - start) * 1000
            debug.log(f"[TIMED] Exit {func.__name__} ({elapsed:.1f}ms)")

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


@contextmanager
def debug_section(name: str):
    """上下文管理器：标记调试区块"""
    debug = DebugMode()
    if debug.enabled:
        debug.log(f"[SECTION] >>> {name}")
    try:
        yield
    finally:
        if debug.enabled:
            debug.log(f"[SECTION] <<< {name}")


# 导入 asyncio 用于装饰器判断
import asyncio
