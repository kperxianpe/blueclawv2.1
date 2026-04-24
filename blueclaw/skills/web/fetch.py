#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Fetch Skill

Fetch web page content with timeout and encoding handling.
"""

import asyncio
import urllib.request
from typing import Optional, Dict
from urllib.error import URLError, HTTPError
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class WebFetchSkill(Skill):
    name = "web_fetch"
    description = "获取网页内容，支持超时和编码处理"
    category = "web"
    
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "目标URL"
            },
            "timeout": {
                "type": "integer",
                "default": 10,
                "description": "请求超时时间（秒）"
            },
            "headers": {
                "type": "object",
                "description": "自定义HTTP请求头"
            },
            "encoding": {
                "type": "string",
                "description": "指定编码（默认自动检测）"
            }
        },
        "required": ["url"]
    }
    
    capabilities = {
        "can_handle": ["HTTP/HTTPS", "HTML页面", "文本内容", "API响应"],
        "cannot_handle": ["需要登录的页面", "JavaScript渲染", "大文件下载"],
        "typical_use_cases": [
            "获取网页内容",
            "调用API接口",
            "检查网页状态",
            "提取文本信息"
        ]
    }
    
    examples = [
        {
            "description": "获取网页内容",
            "input": {"url": "https://example.com"},
            "output": "<!DOCTYPE html>..."
        },
        {
            "description": "带自定义Header",
            "input": {
                "url": "https://api.example.com/data",
                "headers": {"Authorization": "Bearer token"}
            },
            "output": "{\"data\": ...}"
        }
    ]
    
    async def execute(self, url: str, timeout: int = 10,
                     headers: Dict = None, encoding: str = None) -> SkillResult:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            return SkillResult(
                success=False,
                output=None,
                error_message="URL必须以 http:// 或 https:// 开头"
            )
        
        # Default headers
        request_headers = {
            'User-Agent': 'Blueclaw-Skill/1.0'
        }
        if headers:
            request_headers.update(headers)
        
        try:
            req = urllib.request.Request(url, headers=request_headers)
            
            # Execute with timeout using asyncio
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: urllib.request.urlopen(req, timeout=timeout)
                ),
                timeout=timeout + 2  # Slightly longer timeout for asyncio
            )
            
            # Read content
            content = response.read()
            
            # Detect encoding
            if encoding is None:
                content_type = response.headers.get('Content-Type', '')
                if 'charset=' in content_type:
                    encoding = content_type.split('charset=')[-1].split(';')[0]
                else:
                    encoding = 'utf-8'
            
            try:
                text = content.decode(encoding)
            except UnicodeDecodeError:
                text = content.decode('utf-8', errors='replace')
            
            return SkillResult(
                success=True,
                output=text,
                metadata={
                    "url": url,
                    "status_code": response.getcode(),
                    "content_type": response.headers.get('Content-Type'),
                    "content_length": len(content),
                    "encoding": encoding
                }
            )
            
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"请求超时（{timeout}秒）",
                suggestion="增加timeout参数，或检查网络连接"
            )
        except HTTPError as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"HTTP错误 {e.code}: {e.reason}",
                suggestion=f"检查URL是否正确，状态码: {e.code}"
            )
        except URLError as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"URL错误: {e.reason}",
                suggestion="检查网络连接和URL格式"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
