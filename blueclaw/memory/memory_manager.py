# -*- coding: utf-8 -*-
"""Memory Manager - Unified interface"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

from .working_memory import WorkingMemory
from .long_term_memory import LongTermMemory


class MemoryManager:
    """Unified memory management"""
    
    def __init__(self, storage_path: Optional[str] = None, working_memory_size: int = 20):
        self.working = WorkingMemory(max_messages=working_memory_size)
        self.long_term = LongTermMemory(storage_path=storage_path)
        self.entities: Dict[str, Dict[str, Any]] = {}
    
    async def add_message(self, role: str, content: str, **metadata) -> None:
        self.working.add_message(role, content, **metadata)
        await self._extract_entities_from_message(content)
    
    async def add_experience(self, content: Any, persist: bool = True, **metadata) -> str:
        self.working.add_execution_result(
            step=str(content.get('step', 'unknown')),
            result=content,
            success=content.get('success', True),
            **metadata
        )
        
        if persist:
            return self.long_term.add_experience(content=content, tags=metadata.get('tags', []))
        
        return None
    
    async def _extract_entities_from_message(self, content: str) -> None:
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        for email in emails:
            self.add_entity('email', email, {'value': email})
        
        # URL extraction
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, content)
        for url in urls:
            self.add_entity('url', url, {'value': url})
    
    def add_entity(self, entity_type: str, name: str, properties: Dict[str, Any]) -> None:
        self.entities[f"{entity_type}:{name}"] = {
            'type': entity_type,
            'name': name,
            'properties': properties
        }
        self.long_term.add_entity(entity_type, name, properties)
    
    def get_entity(self, entity_type: str, name: str) -> Optional[Dict[str, Any]]:
        key = f"{entity_type}:{name}"
        return self.entities.get(key)
    
    def search_entities(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for key, entity in self.entities.items():
            if entity_type is None or entity['type'] == entity_type:
                results.append(entity)
        return results
    
    async def search_relevant(self, query: str, include_working: bool = True, include_long_term: bool = True, k: int = 5) -> List[Any]:
        results = []
        
        if include_working:
            results.extend(self.working.search(query))
        
        if include_long_term:
            results.extend(self.long_term.search_similar(query, k=k))
        
        return results[:k]
    
    def get_context_string(self) -> str:
        parts = []
        parts.append(self.working.get_context_string())
        
        if self.entities:
            parts.append("\nKnown Entities:")
            for key, entity in list(self.entities.items())[:5]:
                parts.append(f"- {entity['type']}: {entity['name']}")
        
        return '\n'.join(parts)
    
    def get_working_context(self) -> str:
        return self.working.get_context_string()
    
    def set_goal(self, goal: str) -> None:
        self.working.set_goal(goal)
    
    def set_plan(self, plan: Dict[str, Any]) -> None:
        self.working.set_plan(plan)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.long_term.get_preference(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        self.long_term.add_preference(key, value)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'working_memory': self.working.get_stats(),
            'long_term_memory': self.long_term.get_stats(),
            'entities': len(self.entities)
        }
    
    def clear_working_memory(self) -> None:
        self.working.clear()
    
    def clear_all(self) -> None:
        self.working.clear()
        self.long_term.clear()
        self.entities.clear()
