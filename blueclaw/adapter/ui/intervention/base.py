# -*- coding: utf-8 -*-
"""
InterventionUI 抽象接口 + InterventionResult 数据结构
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class InterventionResult:
    """用户干预输入"""
    type: str                          # "annotation", "text", "button", "skip"
    annotation: Optional[Dict] = None  # 画圈/箭头，坐标归一化 0-1
    text: Optional[str] = None         # 文字描述
    choice: Optional[str] = None       # "retry", "skip", "replan", "abort"
    param_changes: Dict[str, Any] = field(default_factory=dict)  # 重试时修改的参数


class InterventionUI(ABC):
    """干预界面抽象基类"""

    @abstractmethod
    async def show(
        self,
        step: Any,
        screenshot: bytes,
        error_info: Optional[str] = None,
    ) -> InterventionResult:
        """展示干预界面并等待用户输入"""
        ...
