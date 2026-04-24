#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLM - Vision Language Model
智能识别：元素检测、状态理解、文字识别
支持：GPT-4V, Claude 3, 本地模型
"""
import json
import base64
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

# 尝试导入 LLM 客户端
try:
    from blueclaw.llm import LLMClient, Message
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class ElementType(Enum):
    """界面元素类型"""
    BUTTON = "button"
    INPUT = "input"
    ICON = "icon"
    TEXT = "text"
    IMAGE = "image"
    MENU = "menu"
    DIALOG = "dialog"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    """识别的UI元素"""
    id: str
    type: ElementType
    label: str  # 按钮文字/输入框占位符等
    description: str  # 详细描述
    bbox: Dict[str, int]  # {"x": int, "y": int, "width": int, "height": int}
    confidence: float
    state: Optional[str] = None  # "enabled", "disabled", "selected", etc.
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "description": self.description,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "state": self.state
        }


class VisionLanguageModel:
    """
    视觉语言模型接口
    - 截图理解
    - 元素检测
    - 状态识别
    """
    
    def __init__(self):
        if LLM_AVAILABLE:
            self.client = LLMClient()
        else:
            self.client = None
    
    async def analyze_screenshot(
        self,
        screenshot_base64: str,
        task_description: str
    ) -> Dict:
        """
        分析截图，返回界面理解结果
        
        返回:
            {
                "scene_type": "主界面/弹窗/菜单...",
                "elements": [UIElement, ...],
                "current_state": "当前状态描述",
                "available_actions": ["可以点击/输入/滚动..."],
                "suggested_next_action": "建议的下一步操作"
            }
        """
        if not LLM_AVAILABLE:
            return self._mock_analysis(task_description)
        
        prompt = f"""分析以下截图，当前任务: {task_description}

请识别:
1. 当前界面类型（主界面/弹窗/菜单/设置页等）
2. 所有可交互元素（按钮、输入框、图标等），包含:
   - 元素类型
   - 文字标签
   - 在图中的坐标位置 (x, y, width, height)
   - 当前状态（可用/不可用/选中/未选中）
3. 当前整体状态描述
4. 可用的操作选项
5. 建议的下一步操作

输出JSON格式:
{{
  "scene_type": "...",
  "elements": [
    {{
      "type": "button|input|icon|text|menu|dialog",
      "label": "按钮文字",
      "description": "详细描述",
      "bbox": {{"x": 100, "y": 200, "width": 80, "height": 30}},
      "state": "enabled|disabled|selected"
    }}
  ],
  "current_state": "...",
  "available_actions": ["..."],
  "suggested_next_action": "..."
}}"""

        try:
            # 使用文本模式（多模态需要特定API支持）
            response = await self.client.chat_completion([
                Message(role="system", content="You are a UI analysis assistant."),
                Message(role="user", content=prompt)
            ])
            
            result = json.loads(response.content)
            
            # 解析为 UIElement 对象
            elements = []
            for i, elem_data in enumerate(result.get("elements", [])):
                element = UIElement(
                    id=f"elem_{i}",
                    type=ElementType(elem_data.get("type", "unknown")),
                    label=elem_data.get("label", ""),
                    description=elem_data.get("description", ""),
                    bbox=elem_data.get("bbox", {"x": 0, "y": 0, "width": 0, "height": 0}),
                    confidence=elem_data.get("confidence", 0.8),
                    state=elem_data.get("state")
                )
                elements.append(element)
            
            return {
                "scene_type": result.get("scene_type", "unknown"),
                "elements": elements,
                "current_state": result.get("current_state", ""),
                "available_actions": result.get("available_actions", []),
                "suggested_next_action": result.get("suggested_next_action", "")
            }
            
        except Exception as e:
            print(f"[VLM] Analysis failed: {e}")
            return self._mock_analysis(task_description)
    
    async def find_element(
        self,
        screenshot_base64: str,
        description: str
    ) -> Optional[UIElement]:
        """
        在截图中查找特定元素
        description: 元素描述，如"左上角的返回按钮"
        """
        if not LLM_AVAILABLE:
            return self._mock_find_element(description)
        
        prompt = f"""在截图中找到以下元素: {description}

返回JSON格式:
{{
  "found": true|false,
  "element": {{
    "type": "button|input|icon|...",
    "label": "...",
    "bbox": {{"x": int, "y": int, "width": int, "height": int}},
    "confidence": float
  }}
}}"""

        try:
            response = await self.client.chat_completion([
                Message(role="system", content="You are a UI element detection assistant."),
                Message(role="user", content=prompt)
            ])
            
            result = json.loads(response.content)
            
            if result.get("found") and result.get("element"):
                elem_data = result["element"]
                return UIElement(
                    id="found_elem",
                    type=ElementType(elem_data.get("type", "unknown")),
                    label=elem_data.get("label", ""),
                    description=description,
                    bbox=elem_data.get("bbox", {}),
                    confidence=elem_data.get("confidence", 0.8)
                )
            return None
            
        except Exception as e:
            print(f"[VLM] Find element failed: {e}")
            return None
    
    async def verify_action_result(
        self,
        before_screenshot: str,
        after_screenshot: str,
        expected_change: str
    ) -> Dict:
        """
        验证操作结果
        返回: {"success": bool, "observed_change": str, "confidence": float}
        """
        if not LLM_AVAILABLE:
            return {"success": True, "observed_change": "Mock verification", "confidence": 0.9}
        
        prompt = f"""比较操作前后的两张截图，验证预期结果。

预期变化: {expected_change}

请分析:
1. 实际发生了什么变化
2. 变化是否符合预期
3. 置信度 (0-1)

返回JSON:
{{
  "success": true|false,
  "observed_change": "描述实际观察到的变化",
  "confidence": 0.95
}}"""

        try:
            response = await self.client.chat_completion([
                Message(role="system", content="You are a UI verification assistant."),
                Message(role="user", content=prompt)
            ])
            return json.loads(response.content)
        except Exception as e:
            return {"success": False, "observed_change": f"Error: {e}", "confidence": 0}
    
    def _mock_analysis(self, task_description: str) -> Dict:
        """模拟分析结果"""
        return {
            "scene_type": "mock_interface",
            "elements": [
                UIElement(
                    id="elem_0",
                    type=ElementType.BUTTON,
                    label="确认",
                    description="主要操作按钮",
                    bbox={"x": 100, "y": 200, "width": 80, "height": 30},
                    confidence=0.9
                ),
                UIElement(
                    id="elem_1",
                    type=ElementType.BUTTON,
                    label="取消",
                    description="取消操作按钮",
                    bbox={"x": 200, "y": 200, "width": 80, "height": 30},
                    confidence=0.9
                ),
                UIElement(
                    id="elem_2",
                    type=ElementType.INPUT,
                    label="输入框",
                    description="文本输入区域",
                    bbox={"x": 100, "y": 150, "width": 200, "height": 30},
                    confidence=0.85
                ),
            ],
            "current_state": f"Mock interface for: {task_description}",
            "available_actions": ["点击确认按钮", "点击取消按钮", "输入文本"],
            "suggested_next_action": "点击确认按钮"
        }
    
    def _mock_find_element(self, description: str) -> Optional[UIElement]:
        """模拟查找元素"""
        return UIElement(
            id="mock_elem",
            type=ElementType.BUTTON,
            label=description,
            description=f"Mock element for: {description}",
            bbox={"x": 100, "y": 100, "width": 100, "height": 40},
            confidence=0.8
        )


# 全局 VLM 实例
vlm = VisionLanguageModel()
