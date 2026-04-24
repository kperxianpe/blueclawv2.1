#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务数据模型
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import time


class TaskStatus(Enum):
    CREATED = "created"
    THINKING = "thinking"
    THINKING_COMPLETED = "thinking_completed"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务实例"""
    id: str
    user_input: str
    status: TaskStatus
    created_at: float
    updated_at: float
    
    # 关联数据（后续填充）
    thinking_path: List[dict] = field(default_factory=list)
    execution_blueprint: Optional[dict] = None
    current_step_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, user_input: str) -> "Task":
        now = time.time()
        return cls(
            id=f"task_{uuid.uuid4().hex[:8]}",
            user_input=user_input,
            status=TaskStatus.CREATED,
            created_at=now,
            updated_at=now
        )
    
    def update_status(self, status: TaskStatus):
        self.status = status
        self.updated_at = time.time()
    
    def to_dict(self) -> dict:
        # Handle both enum and string status
        if isinstance(self.status, TaskStatus):
            status_value = self.status.value
        else:
            status_value = self.status
        
        return {
            "id": self.id,
            "user_input": self.user_input,
            "status": status_value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "thinking_path": self.thinking_path,
            "execution_blueprint": self.execution_blueprint,
            "current_step_id": self.current_step_id
        }
