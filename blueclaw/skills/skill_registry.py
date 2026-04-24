# -*- coding: utf-8 -*-
"""Skill Registry - Central registry for all skills"""

from __future__ import annotations

from typing import Dict, List, Optional, Any

from .base_skill import BaseSkill, SkillResult
from .file_skill import FileSkill
from .shell_skill import ShellSkill
from .code_skill import CodeSkill
from .search_skill import SearchSkill
from .browser_skill import BrowserSkill


class SkillRegistry:
    """Central registry for all skills"""
    
    _instance: Optional[SkillRegistry] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: Dict[str, BaseSkill] = {}
            cls._instance._register_defaults()
        return cls._instance
    
    def _register_defaults(self):
        defaults = [
            FileSkill(), ShellSkill(), CodeSkill(), SearchSkill(), BrowserSkill()
        ]
        for skill in defaults:
            self.register(skill)
    
    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill
    
    def unregister(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)
    
    def has(self, name: str) -> bool:
        return name in self._skills
    
    async def execute(self, name: str, **kwargs) -> SkillResult:
        skill = self.get(name)
        if not skill:
            return SkillResult.fail(error=f"Skill not found: {name}")
        return await skill.run(**kwargs)
    
    def list_skills(self) -> List[str]:
        return list(self._skills.keys())
    
    def get_all_skills(self) -> Dict[str, BaseSkill]:
        return dict(self._skills)
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        return [skill.to_schema() for skill in self._skills.values()]
    
    def get_skill_for_task(self, task_description: str) -> Optional[BaseSkill]:
        task_lower = task_description.lower()
        keywords = {
            'browser': ['browse', 'web', 'url', 'click', 'page', 'website'],
            'file': ['file', 'read', 'write', 'save', 'load', 'folder', 'directory'],
            'shell': ['shell', 'command', 'terminal', 'bash', 'run', 'execute'],
            'code': ['code', 'python', 'script', 'program', 'function'],
            'search': ['search', 'find', 'google', 'lookup', 'query'],
        }
        for skill_name, skill_keywords in keywords.items():
            if any(kw in task_lower for kw in skill_keywords):
                return self.get(skill_name)
        return None


def get_registry() -> SkillRegistry:
    return SkillRegistry()
