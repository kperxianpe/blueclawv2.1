# -*- coding: utf-8 -*-
"""Long-term Memory - Persistent storage"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os


@dataclass
class MemoryRecord:
    """Memory record"""
    id: str
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


class LongTermMemory:
    """Long-term memory for persistent storage"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        
        self.experiences: List[MemoryRecord] = []
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.preferences: Dict[str, Any] = {}
        
        if storage_path and os.path.exists(storage_path):
            self._load()
    
    def _load(self):
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.experiences = [
                MemoryRecord(
                    id=e['id'],
                    content=e['content'],
                    tags=e.get('tags', [])
                )
                for e in data.get('experiences', [])
            ]
            self.entities = data.get('entities', {})
            self.preferences = data.get('preferences', {})
        except Exception as e:
            print(f"Failed to load LTM: {e}")
    
    def _save(self):
        if not self.storage_path:
            return
        
        try:
            data = {
                'experiences': [
                    {'id': e.id, 'content': e.content, 'tags': e.tags}
                    for e in self.experiences
                ],
                'entities': self.entities,
                'preferences': self.preferences
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save LTM: {e}")
    
    def add_experience(self, content: Any, tags: List[str] = None) -> str:
        import uuid
        record_id = str(uuid.uuid4())[:8]
        record = MemoryRecord(id=record_id, content=content, tags=tags or [])
        
        self.experiences.append(record)
        self._save()
        
        return record_id
    
    def add_entity(self, entity_type: str, name: str, properties: Dict[str, Any]):
        key = f"{entity_type}:{name}"
        self.entities[key] = {
            'type': entity_type,
            'name': name,
            'properties': properties
        }
        self._save()
    
    def get_entity(self, entity_type: str, name: str) -> Optional[Dict[str, Any]]:
        key = f"{entity_type}:{name}"
        return self.entities.get(key)
    
    def add_preference(self, key: str, value: Any):
        self.preferences[key] = value
        self._save()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.preferences.get(key, default)
    
    def search_similar(self, query: str, k: int = 5) -> List[MemoryRecord]:
        query_lower = query.lower()
        results = []
        
        for record in self.experiences:
            content_str = json.dumps(record.content).lower()
            tags_str = ' '.join(record.tags).lower()
            
            if query_lower in content_str or query_lower in tags_str:
                results.append(record)
        
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:k]
    
    def clear(self):
        self.experiences.clear()
        self.entities.clear()
        self.preferences.clear()
        self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'experiences': len(self.experiences),
            'entities': len(self.entities),
            'preferences': len(self.preferences)
        }
