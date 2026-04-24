# -*- coding: utf-8 -*-
"""Base Skill class for Blueclaw"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import asyncio
import time


class PermissionLevel(Enum):
    """Permission levels for skills"""
    READ_ONLY = "read_only"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    SYSTEM = "system"


@dataclass
class SkillResult:
    """Result of skill execution"""
    success: bool
    data: Any = None
    error: str = ""
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def ok(cls, data: Any = None, **kwargs) -> SkillResult:
        return cls(success=True, data=data, **kwargs)
    
    @classmethod
    def fail(cls, error: str, **kwargs) -> SkillResult:
        return cls(success=False, error=error, **kwargs)


@dataclass
class SkillParameter:
    """Skill parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


class BaseSkill(ABC):
    """Base class for all Blueclaw skills"""
    
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    parameters: List[SkillParameter] = []
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    requires_confirmation: bool = False
    timeout: float = 60.0
    retry_count: int = 1
    
    def __init__(self):
        self._execution_count = 0
        self._success_count = 0
        self._confirmation_callback: Optional[Callable[[str], bool]] = None
    
    def set_confirmation_callback(self, callback: Callable[[str], bool]):
        self._confirmation_callback = callback
    
    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        pass
    
    async def run(self, **kwargs) -> SkillResult:
        start_time = time.time()
        self._execution_count += 1
        
        try:
            self._validate_params(kwargs)
            
            if self.requires_confirmation or self.permission_level in [
                PermissionLevel.DESTRUCTIVE, PermissionLevel.SYSTEM
            ]:
                if not await self._request_confirmation(kwargs):
                    return SkillResult.fail(
                        error="Operation cancelled by user",
                        duration_ms=(time.time() - start_time) * 1000
                    )
            
            result = await asyncio.wait_for(
                self.execute(**kwargs),
                timeout=self.timeout
            )
            
            if result.success:
                self._success_count += 1
            
            result.duration_ms = (time.time() - start_time) * 1000
            return result
            
        except asyncio.TimeoutError:
            return SkillResult.fail(
                error=f"Skill {self.name} timed out after {self.timeout}s",
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return SkillResult.fail(
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def _validate_params(self, params: Dict[str, Any]) -> None:
        for param in self.parameters:
            if param.required and param.name not in params:
                raise ValueError(f"Missing required parameter: {param.name}")
            if param.name in params and param.enum:
                value = params[param.name]
                if value not in param.enum:
                    raise ValueError(f"Invalid value for {param.name}: {value}")
    
    async def _request_confirmation(self, params: Dict[str, Any]) -> bool:
        if not self._confirmation_callback:
            return True
        message = f"Allow {self.name} with parameters: {params}?"
        return self._confirmation_callback(message)
    
    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "permission_level": self.permission_level.value,
            "requires_confirmation": self.requires_confirmation,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum
                }
                for p in self.parameters
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "execution_count": self._execution_count,
            "success_count": self._success_count,
            "success_rate": self._success_count / max(1, self._execution_count)
        }
