# -*- coding: utf-8 -*-
"""Search Skill - Web search capabilities"""

from __future__ import annotations

from typing import Optional, Dict, Any
from urllib.parse import quote_plus

from .base_skill import BaseSkill, SkillResult, SkillParameter, PermissionLevel


class SearchSkill(BaseSkill):
    """Web search skill"""
    
    name = "search"
    description = "Web search - Google, Bing, Baidu"
    version = "1.0.0"
    permission_level = PermissionLevel.READ_ONLY
    timeout = 30.0
    
    parameters = [
        SkillParameter("query", "string", "Search query", required=True),
        SkillParameter("engine", "string", "Search engine", required=False, default="google"),
    ]
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        super().__init__()
        self.api_keys = api_keys or {}
    
    async def execute(self, **kwargs) -> SkillResult:
        query = kwargs.get('query')
        if not query:
            return SkillResult.fail(error="Missing required parameter: query")
        
        engine = kwargs.get('engine', 'google')
        
        try:
            return await self._search_browser(query, engine)
        except Exception as e:
            return SkillResult.fail(error=f"Search failed: {str(e)}")
    
    async def _search_browser(self, query: str, engine: str) -> SkillResult:
        try:
            from .browser_skill import BrowserSkill
            browser = BrowserSkill()
            
            urls = {
                'google': f'https://www.google.com/search?q={quote_plus(query)}',
                'bing': f'https://www.bing.com/search?q={quote_plus(query)}',
            }
            
            url = urls.get(engine, urls['google'])
            result = await browser.execute(action='navigate', url=url)
            
            if result.success:
                extract_result = await browser.execute(action='extract', selector='h3')
                if extract_result.success:
                    titles = extract_result.data if isinstance(extract_result.data, list) else []
                    results = [{'title': t} for t in titles[:10]]
                    return SkillResult.ok(
                        data=results,
                        metadata={'engine': engine, 'count': len(results)}
                    )
            
            return result
        except ImportError:
            return SkillResult.fail(error="Browser search requires playwright")
        except Exception as e:
            return SkillResult.fail(error=f"Browser search failed: {str(e)}")
