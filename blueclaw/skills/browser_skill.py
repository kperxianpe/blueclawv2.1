# -*- coding: utf-8 -*-
"""Browser Skill - Web automation"""

from __future__ import annotations

from typing import Optional, Dict, Any

from .base_skill import BaseSkill, SkillResult, SkillParameter, PermissionLevel


class BrowserSkill(BaseSkill):
    """Browser automation skill"""
    
    name = "browser"
    description = "Web browser automation - navigate, click, extract"
    version = "1.0.0"
    permission_level = PermissionLevel.READ_ONLY
    timeout = 60.0
    
    parameters = [
        SkillParameter("action", "string", "Action: navigate, click, extract, screenshot, close", required=True),
        SkillParameter("url", "string", "URL to navigate", required=False),
        SkillParameter("selector", "string", "CSS selector", required=False),
        SkillParameter("text", "string", "Text content", required=False),
    ]
    
    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser = None
        self._page = None
    
    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get('action')
        if not action:
            return SkillResult.fail(error="Missing required parameter: action")
        
        try:
            if action == 'navigate':
                return await self._navigate(kwargs.get('url'))
            elif action == 'click':
                return await self._click(kwargs.get('selector'))
            elif action == 'extract':
                return await self._extract(kwargs.get('selector'))
            elif action == 'close':
                return await self._close()
            else:
                return SkillResult.fail(error=f"Unknown action: {action}")
        except Exception as e:
            return SkillResult.fail(error=f"Browser action failed: {str(e)}")
    
    async def _init_browser(self):
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
                self._page = await self._browser.new_page()
            except ImportError:
                raise RuntimeError("Playwright not installed")
    
    async def _navigate(self, url: Optional[str]) -> SkillResult:
        if not url:
            return SkillResult.fail(error="Missing URL")
        
        await self._init_browser()
        response = await self._page.goto(url, wait_until='networkidle')
        
        return SkillResult.ok(
            data={
                'url': self._page.url,
                'title': await self._page.title(),
                'status': response.status if response else None
            }
        )
    
    async def _click(self, selector: Optional[str]) -> SkillResult:
        await self._init_browser()
        if not selector:
            return SkillResult.fail(error="Missing selector")
        
        await self._page.click(selector)
        return SkillResult.ok(data={'clicked': selector})
    
    async def _extract(self, selector: Optional[str]) -> SkillResult:
        await self._init_browser()
        
        if selector:
            elements = await self._page.query_selector_all(selector)
            data = []
            for el in elements:
                text = await el.text_content()
                data.append(text.strip() if text else '')
        else:
            data = await self._page.content()
        
        return SkillResult.ok(data=data)
    
    async def _close(self) -> SkillResult:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        return SkillResult.ok(data='Browser closed')
