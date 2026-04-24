# -*- coding: utf-8 -*-
"""Working Memory - Current session context"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import deque
from datetime import datetime
import json


@dataclass
class MemoryEntry:
    """Memory entry"""
    type: str
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """Working memory for current session"""
    
    def __init__(self, max_messages: int = 20, max_executions: int = 5):
        self.max_messages = max_messages
        self.max_executions = max_executions
        
        self.messages: deque = deque(maxlen=max_messages)
        self.executions: deque = deque(maxlen=max_executions)
        self.thoughts: deque = deque(maxlen=10)
        
        self.current_goal: Optional[str] = None
        self.current_plan: Optional[Dict] = None
        self.session_start = datetime.now()
    
    def add_message(self, role: str, content: str, **metadata) -> None:
        entry = MemoryEntry(
            type='message',
            content={'role': role, 'content': content},
            metadata=metadata
        )
        self.messages.append(entry)
    
    def add_execution_result(self, step: str, result: Any, success: bool = True, **metadata) -> None:
        entry = MemoryEntry(
            type='execution',
            content={'step': step, 'result': result, 'success': success},
            metadata=metadata
        )
        self.executions.append(entry)
    
    def add_thought(self, thought: str, **metadata) -> None:
        entry = MemoryEntry(
            type='thought',
            content=thought,
            metadata=metadata
        )
        self.thoughts.append(entry)
    
    def get_recent_messages(self, n: int = 5) -> List[Dict[str, Any]]:
        recent = list(self.messages)[-n:]
        return [
            {'role': e.content['role'], 'content': e.content['content']}
            for e in recent if e.type == 'message'
        ]
    
    def get_recent_executions(self, n: int = 3) -> List[Dict[str, Any]]:
        recent = list(self.executions)[-n:]
        return [
            {'step': e.content['step'], 'success': e.content['success'], 'result': e.content['result']}
            for e in recent
        ]
    
    def get_context_string(self) -> str:
        parts = []
        
        if self.current_goal:
            parts.append(f"Current Goal: {self.current_goal}")
        
        if self.messages:
            parts.append("\nRecent Conversation:")
            for msg in self.get_recent_messages(10):
                parts.append(f"{msg['role']}: {msg['content']}")
        
        if self.executions:
            parts.append("\nRecent Executions:")
            for exec in self.get_recent_executions(3):
                status = "OK" if exec['success'] else "FAIL"
                parts.append(f"[{status}] {exec['step']}")
        
        return '\n'.join(parts)
    
    def search(self, query: str) -> List[MemoryEntry]:
        query_lower = query.lower()
        results = []
        
        for entry in list(self.messages) + list(self.executions):
            content_str = json.dumps(entry.content).lower()
            if query_lower in content_str:
                results.append(entry)
        
        return results
    
    def set_goal(self, goal: str) -> None:
        self.current_goal = goal
    
    def set_plan(self, plan: Dict[str, Any]) -> None:
        self.current_plan = plan
    
    def clear(self) -> None:
        self.messages.clear()
        self.executions.clear()
        self.thoughts.clear()
        self.current_goal = None
        self.current_plan = None
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'messages': len(self.messages),
            'executions': len(self.executions),
            'thoughts': len(self.thoughts),
            'session_start': self.session_start.isoformat(),
            'current_goal': self.current_goal
        }
