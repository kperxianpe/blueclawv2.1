#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HEE - Hybrid Execution Engine
混合执行引擎：双通路调度

视觉通路: 截图 -> 识别 -> 点击 -> 验证
函数通路: 直接调用应用API
"""
import asyncio
from typing import Optional, Dict, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from .vms import vms
from .vlm import vlm, UIElement
from .mpl import mpl

if TYPE_CHECKING:
    from blueclaw.core.execution_engine import ExecutionStep


class ExecutionMode(Enum):
    """执行模式"""
    VISUAL = "visual"      # 视觉通路（截图+鼠标）
    FUNCTION = "function"  # 函数通路（API调用）
    HYBRID = "hybrid"      # 混合（自动选择）


@dataclass
class ExecutionPlan:
    """执行计划"""
    mode: ExecutionMode
    steps: List[Dict]  # 执行步骤列表
    fallback: Optional[str] = None  # 失败时的备选方案


class HybridExecutionEngine:
    """
    混合执行引擎
    根据任务类型智能选择视觉通路或函数通路
    """
    
    def __init__(self):
        self.vms = vms
        self.vlm = vlm
        self.mpl = mpl
    
    async def execute(
        self,
        task_id: str,
        step: 'ExecutionStep',
        mode: ExecutionMode = ExecutionMode.HYBRID
    ) -> Dict:
        """
        执行步骤
        
        流程:
        1. 如果是函数调用模式，直接调用API
        2. 如果是视觉模式，截图 -> 识别 -> 操作 -> 验证
        3. 返回执行结果
        """
        if mode == ExecutionMode.FUNCTION or self._should_use_function(step):
            return await self._execute_function_path(task_id, step)
        else:
            return await self._execute_visual_path(task_id, step)
    
    async def _execute_visual_path(self, task_id: str, step: 'ExecutionStep') -> Dict:
        """
        视觉通路执行
        1. 截图
        2. VLM识别
        3. 执行动作
        4. 验证结果
        """
        results = []
        
        # 1. 截图
        screenshot = await self.vms.capture_fullscreen(task_id)
        if not screenshot:
            return {"success": False, "error": "Screenshot failed"}
        
        # 2. VLM识别
        analysis = await self.vlm.analyze_screenshot(
            screenshot.base64,
            step.direction
        )
        
        # 3. 根据识别结果执行动作
        suggested_action = analysis.get("suggested_next_action", "")
        elements = analysis.get("elements", [])
        
        # 找到目标元素并执行点击
        target_element = self._find_target_element(elements, step.direction)
        
        if target_element:
            # 在截图上标注目标元素
            self.vms.add_annotation(
                screenshot.id,
                "circle",
                target_element.bbox,
                label=target_element.label,
                color="#00FF00"
            )
            
            # 执行点击
            center_x = target_element.bbox["x"] + target_element.bbox["width"] // 2
            center_y = target_element.bbox["y"] + target_element.bbox["height"] // 2
            
            action_result = await self.mpl.click(center_x, center_y)
            results.append(action_result)
            
            # 4. 验证结果（截图对比）
            await asyncio.sleep(0.5)
            after_screenshot = await self.vms.capture_fullscreen(task_id)
            
            if after_screenshot:
                verification = await self.vlm.verify_action_result(
                    screenshot.base64,
                    after_screenshot.base64,
                    step.validation
                )
                
                return {
                    "success": verification.get("success", False),
                    "action_results": [r.to_dict() for r in results],
                    "verification": verification,
                    "screenshots": {
                        "before": screenshot.id,
                        "after": after_screenshot.id
                    },
                    "target_element": target_element.to_dict()
                }
        
        return {
            "success": False,
            "error": "Target element not found",
            "analysis": {
                "scene_type": analysis.get("scene_type"),
                "elements_count": len(elements),
                "suggested_action": suggested_action
            },
            "action_results": [r.to_dict() for r in results]
        }
    
    async def _execute_function_path(self, task_id: str, step: 'ExecutionStep') -> Dict:
        """
        函数通路执行
        直接调用应用API或工具
        """
        # TODO: 调用具体的工具/技能
        return {
            "success": True,
            "mode": "function",
            "message": f"Executed function for: {step.direction}"
        }
    
    def _should_use_function(self, step: 'ExecutionStep') -> bool:
        """判断是否应使用函数通路"""
        # 如果工具是API类型，使用函数通路
        if step.tool.lower() in ["api", "skill", "mcp"]:
            return True
        # 如果工具是VisAdapter或视觉相关，使用视觉通路
        if "vis" in step.tool.lower() or "adapter" in step.tool.lower():
            return False
        # 默认使用视觉通路
        return False
    
    def _find_target_element(self, elements: List[UIElement], direction: str) -> Optional[UIElement]:
        """根据方向描述找到目标元素"""
        direction_lower = direction.lower()
        
        # 简单匹配：找最相关的元素
        for elem in elements:
            if elem.type.value in ["button", "icon"] and elem.label:
                label_lower = elem.label.lower()
                # 检查方向描述中是否包含元素的标签
                if any(word in label_lower for word in direction_lower.split()):
                    return elem
                # 检查常见操作关键词
                if "点击" in direction and elem.type.value == "button":
                    return elem
                if "输入" in direction and elem.type.value == "input":
                    return elem
        
        # 如果没找到，返回第一个可点击元素
        for elem in elements:
            if elem.type.value in ["button", "icon"]:
                return elem
        
        return None
    
    async def execute_with_adapter(
        self,
        task_id: str,
        step: 'ExecutionStep',
        adapter=None
    ) -> Dict:
        """
        使用应用适配器执行
        适配器可以提供元素提示和前后处理
        """
        if adapter:
            # 预处理
            should_continue = await adapter.before_visual_action(
                step.direction, {}
            )
            if not should_continue:
                return {"success": True, "message": "Skipped by adapter"}
        
        # 执行视觉通路
        result = await self._execute_visual_path(task_id, step)
        
        if adapter:
            # 后处理
            result = await adapter.after_visual_action(step.direction, result)
        
        return result
    
    async def execute_action_sequence(
        self,
        task_id: str,
        actions: List[Dict]
    ) -> Dict:
        """
        执行动作序列
        actions: [{"action": "click", "x": 100, "y": 200}, ...]
        """
        results = []
        
        for action_def in actions:
            result = await self.mpl.execute_action(action_def)
            results.append(result.to_dict())
            
            # 如果动作失败，停止序列
            if not result.success:
                return {
                    "success": False,
                    "error": f"Action failed: {result.message}",
                    "completed_actions": len(results) - 1,
                    "results": results
                }
            
            # 动作间等待
            await asyncio.sleep(0.3)
        
        return {
            "success": True,
            "completed_actions": len(results),
            "results": results
        }


# 全局 HEE 实例
hee = HybridExecutionEngine()
