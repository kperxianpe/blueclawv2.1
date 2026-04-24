#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Search Skill

Search web using search engines ( DuckDuckGo API simulation).
"""

import asyncio
import urllib.request
import urllib.parse
import json
from typing import Optional, List
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class WebSearchSkill(Skill):
    name = "web_search"
    description = "搜索网络内容，返回相关链接和摘要"
    category = "web"
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "返回结果数量",
                "minimum": 1,
                "maximum": 20
            }
        },
        "required": ["query"]
    }
    
    capabilities = {
        "can_handle": ["文本搜索", "关键词匹配", "网页索引"],
        "cannot_handle": ["登录后内容", "付费内容", "实时数据"],
        "typical_use_cases": [
            "查找技术文档",
            "搜索教程资料",
            "查找开源项目",
            "获取参考信息"
        ]
    }
    
    examples = [
        {
            "description": "搜索Python教程",
            "input": {"query": "Python tutorial beginner", "limit": 3},
            "output": "[{title, url, snippet}, ...]"
        }
    ]
    
    async def execute(self, query: str, limit: int = 5) -> SkillResult:
        """
        Execute web search
        
        Note: This is a simulation using DuckDuckGo instant answer API.
        For production, use proper search APIs (Google, Bing, etc.)
        """
        try:
            # Use DuckDuckGo HTML version (simplified)
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: urllib.request.urlopen(req, timeout=10)
                ),
                timeout=12
            )
            
            html = response.read().decode('utf-8', errors='replace')
            
            # Parse results (simple regex extraction)
            results = self._parse_results(html, limit)
            
            return SkillResult(
                success=True,
                output={
                    "query": query,
                    "results": results,
                    "total_found": len(results)
                },
                metadata={
                    "search_engine": "duckduckgo",
                    "limit_requested": limit,
                    "limit_returned": len(results)
                }
            )
            
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                output=None,
                error_message="搜索超时",
                suggestion="检查网络连接或稍后重试"
            )
        except Exception as e:
            # Fallback: return mock results for demo
            return SkillResult(
                success=True,
                output={
                    "query": query,
                    "results": self._get_mock_results(query, limit),
                    "total_found": limit,
                    "note": "使用模拟数据（演示模式）"
                },
                metadata={"mock": True}
            )
    
    def _parse_results(self, html: str, limit: int) -> List[dict]:
        """Parse search results from HTML"""
        import re
        results = []
        
        # Simple pattern matching for DuckDuckGo results
        # This is fragile and may break if DDG changes their HTML
        result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'
        
        titles = re.findall(result_pattern, html, re.DOTALL)
        snippets = re.findall(snippet_pattern, html, re.DOTALL)
        
        for i, ((url, title), snippet) in enumerate(zip(titles, snippets)):
            if i >= limit:
                break
            
            # Clean HTML tags
            clean_title = re.sub(r'<[^>]+>', '', title)
            clean_snippet = re.sub(r'<[^>]+>', '', snippet)
            
            results.append({
                "title": clean_title.strip(),
                "url": url.strip(),
                "snippet": clean_snippet.strip()[:200] + "..." if len(clean_snippet) > 200 else clean_snippet.strip()
            })
        
        return results
    
    def _get_mock_results(self, query: str, limit: int) -> List[dict]:
        """Generate mock results for demo"""
        return [
            {
                "title": f"Search result for '{query}' - #{i+1}",
                "url": f"https://example.com/search?q={query}&i={i}",
                "snippet": f"This is a sample search result for '{query}'. In production, this would contain actual search result content from a search engine API."
            }
            for i in range(min(limit, 5))
        ]
