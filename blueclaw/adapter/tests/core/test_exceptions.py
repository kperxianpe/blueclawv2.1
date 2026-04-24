# -*- coding: utf-8 -*-
"""
异常处理测试

- 异常分类
- 本地化消息
- 调试模式
"""
import pytest

from blueclaw.adapter.exceptions import (
    AdapterException, NetworkAdapterException, LocatorAdapterException,
    ExecutionAdapterException, TimeoutAdapterException, ValidationAdapterException,
    SandboxAdapterException, PageLoadAdapterException, ResourceExhaustedAdapterException,
    RetryExhaustedAdapterException, classify_error,
)
from blueclaw.adapter.error_localization import localize_error, get_error_suggestion
from blueclaw.adapter.debug import DebugMode, timed, debug_section


class TestExceptionClassification:
    """异常自动分类测试"""

    def test_classify_timeout(self):
        err = classify_error(TimeoutError("Connection timed out"))
        assert isinstance(err, TimeoutAdapterException)
        assert err.category == "timeout"

    def test_classify_network(self):
        err = classify_error(ConnectionError("Connection refused"))
        assert isinstance(err, NetworkAdapterException)
        assert err.category == "network"

    def test_classify_page_load(self):
        err = classify_error(Exception("404 Not Found"))
        assert isinstance(err, PageLoadAdapterException)
        assert err.category == "page_load"

    def test_classify_resource(self):
        err = classify_error(MemoryError("Out of memory"))
        assert isinstance(err, ResourceExhaustedAdapterException)
        assert err.category == "resource_exhausted"

    def test_classify_locator(self):
        err = classify_error(RuntimeError("Element not found: #submit"))
        assert isinstance(err, LocatorAdapterException)
        assert err.category == "locator"

    def test_classify_execution_fallback(self):
        err = classify_error(ValueError("Something went wrong"))
        assert isinstance(err, ExecutionAdapterException)
        assert err.category == "execution"

    def test_classify_passes_through_adapter_exception(self):
        original = ValidationAdapterException("validation failed")
        result = classify_error(original)
        assert result is original

    def test_classify_with_context(self):
        ctx = {"url": "https://example.com"}
        err = classify_error(TimeoutError("timeout"), context=ctx)
        assert err.context["url"] == "https://example.com"


class TestErrorLocalization:
    """错误消息本地化测试"""

    def test_localize_network_zh(self):
        msg = localize_error("network", "Connection refused", lang="zh")
        assert "网络连接失败" in msg
        assert "Connection refused" in msg

    def test_localize_timeout_en(self):
        msg = localize_error("timeout", "Operation timed out", lang="en")
        assert "timed out" in msg.lower()

    def test_localize_unknown_category(self):
        msg = localize_error("unknown_category", "Some error", lang="zh")
        assert "执行失败" in msg  # 默认归类为 execution

    def test_get_suggestion_network(self):
        sug = get_error_suggestion("network", lang="zh")
        assert "检查网络连接" in sug

    def test_get_suggestion_locator(self):
        sug = get_error_suggestion("locator", lang="zh")
        assert "选择器" in sug

    def test_get_suggestion_unknown(self):
        sug = get_error_suggestion("nonexistent", lang="zh")
        assert sug == ""


class TestDebugMode:
    """调试模式测试"""

    def test_debug_singleton(self):
        d1 = DebugMode()
        d2 = DebugMode()
        assert d1 is d2

    def test_debug_enable_disable(self):
        debug = DebugMode()
        assert debug.enabled is False

        debug.enable()
        assert debug.enabled is True

        debug.disable()
        assert debug.enabled is False

    def test_debug_log_when_disabled(self):
        debug = DebugMode()
        debug.disable()
        # 不应抛出异常
        debug.log("test message")

    def test_debug_log_when_enabled(self):
        debug = DebugMode()
        debug.enable()
        debug.log("test message")
        debug.disable()

    def test_memory_snapshot_without_tracing(self):
        debug = DebugMode()
        debug.disable()
        assert debug.get_memory_snapshot() is None

    def test_debug_section_context_manager(self):
        debug = DebugMode()
        debug.enable()
        with debug_section("test_section"):
            pass
        debug.disable()


class TestExceptionSubclasses:
    """异常子类测试"""

    def test_sandbox_exception(self):
        err = SandboxAdapterException("container crashed", {"container_id": "abc123"})
        assert err.category == "sandbox"
        assert err.context["container_id"] == "abc123"

    def test_page_load_exception(self):
        err = PageLoadAdapterException("SSL certificate invalid")
        assert err.category == "page_load"

    def test_resource_exhausted_exception(self):
        err = ResourceExhaustedAdapterException("Disk full")
        assert err.category == "resource_exhausted"

    def test_retry_exhausted_exception(self):
        err = RetryExhaustedAdapterException("All retries failed")
        assert err.category == "retry_exhausted"

    def test_exception_to_dict(self):
        err = NetworkAdapterException("timeout", {"url": "http://test.com"})
        d = err.to_dict()
        assert d["category"] == "network"
        assert d["message"] == "timeout"
        assert d["context"]["url"] == "http://test.com"
        assert "timestamp" in d
