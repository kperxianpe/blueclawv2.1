#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid Execution Controller (HEC)

- 自愈: 元素找不到时等待重试
- 循环保护: 同一步骤最大执行次数限制
- 降级: 失败时自动暂停或回退

对接 AdapterManager，不替换现有逻辑，只在外层包装。
"""

import asyncio
import time
from typing import Callable, Dict, Optional, Any


class HybridExecutionController:
    """混合执行控制器 — 自愈 + 循环保护"""

    def __init__(self, max_retries: int = 2, max_loop: int = 10, retry_delay: float = 0.5):
        self.max_retries = max_retries
        self.max_loop = max_loop
        self.retry_delay = retry_delay
        self.loop_counters: Dict[str, int] = {}
        self._last_retry_time: Dict[str, float] = {}

    async def execute_with_recovery(
        self,
        step_id: str,
        action: Callable[[], Any],
        on_failure: str = "retry",
    ) -> Dict[str, Any]:
        """
        带自愈的执行包装。

        Args:
            step_id: 步骤唯一标识
            action: 实际执行的异步函数
            on_failure: 失败策略 — "retry" | "pause" | "skip"

        Returns:
            {"success": bool, "result": any, "retries": int, "requires_intervention": bool}
        """
        for attempt in range(self.max_retries + 1):
            try:
                result = await action()
                return {
                    "success": True,
                    "result": result,
                    "retries": attempt,
                    "requires_intervention": False,
                }
            except Exception as e:
                error_msg = str(e).lower()

                # 自愈策略 1: 元素未就绪 → 等待后重试
                if attempt == 0 and any(kw in error_msg for kw in ("element", "timeout", "not found", "selector")):
                    wait_time = 1.0 * (attempt + 1)
                    await asyncio.sleep(wait_time)
                    continue

                # 自愈策略 2: 网络问题 → 指数退避
                if "network" in error_msg or "connection" in error_msg:
                    wait_time = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue

                # 重试次数耗尽
                if attempt >= self.max_retries:
                    if on_failure == "pause":
                        return {
                            "success": False,
                            "error": str(e),
                            "retries": attempt,
                            "requires_intervention": True,
                        }
                    elif on_failure == "skip":
                        return {
                            "success": True,  # 标记为成功但跳过
                            "result": {"skipped": True, "error": str(e)},
                            "retries": attempt,
                            "requires_intervention": False,
                        }
                    return {
                        "success": False,
                        "error": str(e),
                        "retries": attempt,
                        "requires_intervention": False,
                    }

                # 中间失败，指数退避后重试
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        return {
            "success": False,
            "error": "All retries exhausted",
            "retries": self.max_retries + 1,
            "requires_intervention": False,
        }

    def check_loop(self, step_id: str) -> bool:
        """
        循环保护检查。
        同一步骤执行次数超过 max_loop 时返回 False。
        """
        count = self.loop_counters.get(step_id, 0) + 1
        self.loop_counters[step_id] = count
        return count <= self.max_loop

    def reset_loop_counter(self, step_id: str):
        """重置某步骤的循环计数器（步骤成功完成后调用）"""
        self.loop_counters.pop(step_id, None)

    def reset_all(self):
        """重置所有计数器"""
        self.loop_counters.clear()
        self._last_retry_time.clear()


# Global instance
hec = HybridExecutionController()
