#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Registry Module

Central registry for all skills with category-based organization.
"""

from typing import Dict, Type, Optional, List
from .base import Skill


class SkillRegistry:
    """
    Skill Registry
    
    Central registry for managing all skills.
    """
    _skills: Dict[str, Type[Skill]] = {}
    _instances: Dict[str, Skill] = {}
    
    @classmethod
    def register(cls, skill_class: Type[Skill]) -> Type[Skill]:
        """
        Register a skill class
        
        Usage:
            @SkillRegistry.register
            class MySkill(Skill):
                ...
        """
        cls._skills[skill_class.name] = skill_class
        return skill_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Skill]:
        """Get skill instance by name"""
        if name not in cls._instances and name in cls._skills:
            cls._instances[name] = cls._skills[name]()
        return cls._instances.get(name)
    
    @classmethod
    def get_class(cls, name: str) -> Optional[Type[Skill]]:
        """Get skill class by name"""
        return cls._skills.get(name)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered skill names"""
        return list(cls._skills.keys())
    
    @classmethod
    def list_by_category(cls, category: str = None) -> Dict[str, Skill]:
        """
        List skills by category
        
        Args:
            category: Category filter, None for all
            
        Returns:
            Dict of skill_name -> skill_instance
        """
        result = {}
        for name, skill_class in cls._skills.items():
            if category is None or skill_class.category == category:
                skill = cls.get(name)
                if skill:
                    result[name] = skill
        return result
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for skill_class in cls._skills.values():
            categories.add(skill_class.category)
        return sorted(list(categories))
    
    @classmethod
    def clear(cls):
        """Clear all registered skills (for testing)"""
        cls._skills.clear()
        cls._instances.clear()
    
    @classmethod
    def count(cls) -> int:
        """Get total number of registered skills"""
        return len(cls._skills)
    
    @classmethod
    def search(cls, keyword: str) -> List[str]:
        """Search skills by keyword in name or description"""
        results = []
        keyword_lower = keyword.lower()
        for name, skill_class in cls._skills.items():
            if (keyword_lower in name.lower() or 
                keyword_lower in skill_class.description.lower()):
                results.append(name)
        return results
