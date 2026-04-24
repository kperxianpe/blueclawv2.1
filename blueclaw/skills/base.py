#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Base Module

OpenClaw-style Skill architecture with AI dynamic tool selection support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
import time


@dataclass
class SkillResult:
    """Skill execution result"""
    success: bool
    output: Any
    execution_time: float = 0
    error_message: Optional[str] = None
    suggestion: Optional[str] = None  # Error suggestion
    metadata: Dict = field(default_factory=dict)


class Skill(ABC):
    """
    Skill Base Class - OpenClaw style
    
    Supports AI dynamic tool selection through rich metadata.
    """
    # Basic info
    name: str = ""
    description: str = ""
    category: str = ""
    
    # OpenClaw-style definitions
    parameters: Dict = {}              # JSON Schema parameter definitions
    capabilities: Dict = {}            # Capability descriptions
    examples: List[Dict] = []          # Few-shot examples
    
    # Risk management
    dangerous: bool = False            # High risk?
    dangerous_level: int = 0           # Risk level 0-3
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    async def run(self, **params) -> SkillResult:
        """
        Execute skill with validation and error handling
        
        Args:
            **params: Execution parameters
            
        Returns:
            SkillResult: Execution result
        """
        start = time.time()
        
        # Validate parameters
        valid, error = self._validate_params(params)
        if not valid:
            return SkillResult(
                success=False,
                output=None,
                error_message=error,
                execution_time=time.time() - start
            )
        
        try:
            result = await self.execute(**params)
            result.execution_time = time.time() - start
            return result
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e),
                execution_time=time.time() - start,
                suggestion=self._get_error_suggestion(e)
            )
    
    def _validate_params(self, params: Dict) -> tuple:
        """Validate parameters against JSON Schema"""
        required = self.parameters.get('required', [])
        for param in required:
            if param not in params:
                return False, f"Missing required parameter: {param}"
        return True, ""
    
    def _get_error_suggestion(self, error: Exception) -> str:
        """Get error suggestion based on error type"""
        error_str = str(error).lower()
        if "file" in error_str and ("not found" in error_str or "不存在" in error_str):
            return "Check if the path is correct, or use file_list to view directory contents"
        if "permission" in error_str or "权限" in error_str:
            return "Check file permissions, or use system_info to view current user"
        if "encoding" in error_str or "编码" in error_str:
            return "Try using encoding='latin-1' or encoding='gbk' parameter"
        return ""
    
    @abstractmethod
    async def execute(self, **params) -> SkillResult:
        """
        Execute skill logic
        
        Override this method in subclasses.
        """
        pass
    
    def to_dict(self) -> Dict:
        """Convert skill to dictionary for serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters,
            "capabilities": self.capabilities,
            "dangerous": self.dangerous,
            "dangerous_level": self.dangerous_level,
            "examples_count": len(self.examples)
        }
