#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASB - App-Specific Bridge 基类
应用专属桥接器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class AppState:
    """应用状态"""
    app_name: str
    is_running: bool
    current_view: str  # 当前界面
    available_actions: List[str]
    raw_state: Dict  # 原始状态数据


class AppAdapter(ABC):
    """
    应用适配器基类
    每个具体应用（剪映、Blender等）继承此类
    """
    
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.state: Optional[AppState] = None
    
    @abstractmethod
    async def detect_state(self) -> AppState:
        """检测应用当前状态"""
        pass
    
    @abstractmethod
    async def execute_action(self, action: str, params: Dict) -> Dict:
        """执行应用特定操作"""
        pass
    
    @abstractmethod
    def get_element_hints(self) -> Dict[str, Dict]:
        """
        返回应用元素提示
        帮助VLM更准确识别该应用特有的UI元素
        """
        pass
    
    async def before_visual_action(self, action: str, params: Dict) -> bool:
        """
        视觉操作前的预处理
        返回False则跳过视觉操作
        """
        return True
    
    async def after_visual_action(self, action: str, result: Dict) -> Dict:
        """视觉操作后的后处理"""
        return result
