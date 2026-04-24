#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Models - Week 20.5
数据模型定义
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ToolBinding:
    """工具绑定信息 - 存储在 ExecutionStep 中"""
    tool_icon_id: str
    locked: bool = True  # True = 强制使用，False = 仅作为提示
    actual_execution: Optional[Dict[str, Any]] = None  # 运行时回填
    
    def to_dict(self) -> dict:
        return {
            "tool_icon_id": self.tool_icon_id,
            "locked": self.locked,
            "actual_execution": self.actual_execution
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ToolBinding":
        return cls(
            tool_icon_id=data.get("tool_icon_id", ""),
            locked=data.get("locked", True),
            actual_execution=data.get("actual_execution")
        )
