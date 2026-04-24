# -*- coding: utf-8 -*-
"""
Adapter 错误处理框架

- AdapterException 基类及子类
- 错误分类（网络/定位/执行/验证/超时）
- 错误上下文捕获（调用栈、状态快照）
- 结构化日志记录（JSON 格式到 jsonl）
"""
import os
import json
import traceback
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional


# 确保日志目录存在
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_PATH = os.path.join(_LOG_DIR, "adapter_exceptions.jsonl")

# 配置 JSONL 日志处理器
_logger = logging.getLogger("blueclaw.adapter.exceptions")
_logger.setLevel(logging.DEBUG)
if not _logger.handlers:
    _file_handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    _file_handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_file_handler)


def _log_json(record: Dict[str, Any]) -> None:
    _logger.info(json.dumps(record, ensure_ascii=False, default=str))


class AdapterException(Exception):
    """Adapter 异常基类"""

    def __init__(
        self,
        message: str,
        category: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.stack_trace = traceback.format_exc()

        # 自动记录结构化日志
        self._log()

    def _log(self) -> None:
        record = {
            "level": "error",
            "category": self.category,
            "message": self.message,
            "timestamp": self.timestamp,
            "context": self.context,
            "stack_trace": self.stack_trace,
        }
        _log_json(record)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "message": self.message,
            "timestamp": self.timestamp,
            "context": self.context,
            "stack_trace": self.stack_trace,
        }


class NetworkAdapterException(AdapterException):
    """网络相关异常"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="network", context=context)


class LocatorAdapterException(AdapterException):
    """元素/目标定位异常"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="locator", context=context)


class ExecutionAdapterException(AdapterException):
    """执行过程异常"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="execution", context=context)


class ValidationAdapterException(AdapterException):
    """结果验证异常"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="validation", context=context)


class TimeoutAdapterException(AdapterException):
    """超时异常"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="timeout", context=context)


class SandboxAdapterException(AdapterException):
    """沙盒环境异常（容器崩溃、资源不足）"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="sandbox", context=context)


class PageLoadAdapterException(AdapterException):
    """页面加载异常（404/500/超时/证书错误）"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="page_load", context=context)


class ResourceExhaustedAdapterException(AdapterException):
    """资源耗尽异常（内存/CPU/磁盘不足）"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="resource_exhausted", context=context)


class RetryExhaustedAdapterException(AdapterException):
    """重试耗尽异常（所有恢复策略均失败）"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, category="retry_exhausted", context=context)


def classify_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> AdapterException:
    """自动分类异常为 AdapterException 子类

    用于将原始 Python 异常转换为结构化的 AdapterException。
    """
    msg = str(error)
    ctx = context or {}

    if isinstance(error, AdapterException):
        return error

    # 超时相关
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return TimeoutAdapterException(msg, ctx)

    # 网络相关
    if any(k in msg.lower() for k in ("connection", "network", "dns", "refused", "reset")):
        return NetworkAdapterException(msg, ctx)

    # 页面加载
    if any(k in msg.lower() for k in ("404", "500", "403", "net::", "ssl", "certificate")):
        return PageLoadAdapterException(msg, ctx)

    # 资源耗尽
    if any(k in msg.lower() for k in ("memory", "disk", "no space", "too many")):
        return ResourceExhaustedAdapterException(msg, ctx)

    # 元素定位
    if any(k in msg.lower() for k in ("not found", "element", "locator", "selector")):
        return LocatorAdapterException(msg, ctx)

    # 默认归类为执行异常
    return ExecutionAdapterException(msg, ctx)
