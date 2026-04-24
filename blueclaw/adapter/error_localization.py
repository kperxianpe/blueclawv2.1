# -*- coding: utf-8 -*-
"""
Error Localization - 错误消息本地化

- 中文/英文双语支持
- 用户友好的错误提示
- 建议修复方案
"""
from typing import Dict, Any, Optional


# 错误消息模板
ERROR_TEMPLATES: Dict[str, Dict[str, str]] = {
    "network": {
        "zh": "网络连接失败: {message}\n建议: 检查网络连接，稍后重试。",
        "en": "Network connection failed: {message}\nSuggestion: Check your network and retry.",
    },
    "timeout": {
        "zh": "操作超时: {message}\n建议: 增加超时时间或检查目标是否响应。",
        "en": "Operation timed out: {message}\nSuggestion: Increase timeout or check target responsiveness.",
    },
    "locator": {
        "zh": "元素定位失败: {message}\n建议: 检查页面是否加载完成，或更新选择器。",
        "en": "Element not found: {message}\nSuggestion: Ensure page is loaded or update the selector.",
    },
    "page_load": {
        "zh": "页面加载失败: {message}\n建议: 检查 URL 是否正确，或网站是否可用。",
        "en": "Page load failed: {message}\nSuggestion: Verify the URL or check if the site is available.",
    },
    "sandbox": {
        "zh": "沙盒环境异常: {message}\n建议: 检查 Docker/容器状态，或重启沙盒。",
        "en": "Sandbox environment error: {message}\nSuggestion: Check Docker/container status or restart sandbox.",
    },
    "resource_exhausted": {
        "zh": "资源不足: {message}\n建议: 关闭不必要的进程，释放内存/磁盘空间。",
        "en": "Resource exhausted: {message}\nSuggestion: Close unnecessary processes to free memory/disk.",
    },
    "retry_exhausted": {
        "zh": "所有恢复策略已耗尽: {message}\n建议: 检查任务参数，或联系管理员。",
        "en": "All recovery strategies exhausted: {message}\nSuggestion: Check task parameters or contact admin.",
    },
    "execution": {
        "zh": "执行失败: {message}\n建议: 查看详细日志，检查输入参数。",
        "en": "Execution failed: {message}\nSuggestion: Review detailed logs and check input parameters.",
    },
    "validation": {
        "zh": "验证失败: {message}\n建议: 检查预期结果是否与实际匹配。",
        "en": "Validation failed: {message}\nSuggestion: Check if expected results match actual output.",
    },
}


def localize_error(
    category: str,
    message: str,
    lang: str = "zh",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """将错误分类和消息转换为用户友好的本地化提示

    Args:
        category: 错误分类 (network/timeout/locator/...)
        message: 原始错误消息
        lang: 语言代码 (zh/en)
        context: 额外上下文（用于插值）

    Returns:
        用户友好的错误提示字符串
    """
    template = ERROR_TEMPLATES.get(category, ERROR_TEMPLATES["execution"])
    text = template.get(lang, template.get("en", "{message}"))

    # 基础插值
    result = text.format(message=message)

    # 添加上下文信息（调试模式）
    if context and context.get("debug"):
        result += f"\n[Debug Context] {context}"

    return result


def get_error_suggestion(category: str, lang: str = "zh") -> str:
    """获取错误类别的修复建议"""
    suggestions = {
        "network": {
            "zh": "1. 检查网络连接\n2. 确认防火墙设置\n3. 使用代理/VPN 重试",
            "en": "1. Check network connection\n2. Verify firewall settings\n3. Retry with proxy/VPN",
        },
        "timeout": {
            "zh": "1. 增加超时时间（timeout 参数）\n2. 检查目标服务状态\n3. 减少并发请求数",
            "en": "1. Increase timeout parameter\n2. Check target service status\n3. Reduce concurrent requests",
        },
        "locator": {
            "zh": "1. 等待页面完全加载（添加 wait 步骤）\n2. 更新 CSS/XPath 选择器\n3. 使用语义定位替代精确选择器",
            "en": "1. Wait for page to fully load\n2. Update CSS/XPath selectors\n3. Use semantic targeting",
        },
        "page_load": {
            "zh": "1. 验证 URL 拼写\n2. 检查 HTTP 状态码\n3. 确认 SSL 证书有效",
            "en": "1. Verify URL spelling\n2. Check HTTP status code\n3. Ensure SSL certificate is valid",
        },
        "sandbox": {
            "zh": "1. 检查 Docker 守护进程状态\n2. 清理旧的沙盒容器\n3. 增加容器资源限制",
            "en": "1. Check Docker daemon status\n2. Clean up old sandbox containers\n3. Increase container resource limits",
        },
    }
    return suggestions.get(category, {}).get(lang, "")
