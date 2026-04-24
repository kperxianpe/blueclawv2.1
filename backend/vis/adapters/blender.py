#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blender适配器
"""
from typing import Dict
from .base import AppAdapter, AppState


class BlenderAdapter(AppAdapter):
    """Blender适配器"""
    
    def __init__(self):
        super().__init__("Blender")
        self.element_hints = {
            "3D视口": {"region": "center", "mode_indicator": True},
            "时间轴": {"region": "bottom"},
            "属性面板": {"region": "right"},
            "工具栏": {"region": "left"},
            "模式切换": {"region": "top_left", "options": ["物体模式", "编辑模式", "雕刻模式"]},
        }
    
    async def detect_state(self) -> AppState:
        """检测Blender状态"""
        return AppState(
            app_name=self.app_name,
            is_running=True,
            current_view="3d_viewport",
            available_actions=["选择物体", "移动", "旋转", "缩放", "添加物体", "渲染"],
            raw_state={}
        )
    
    async def execute_action(self, action: str, params: Dict) -> Dict:
        """执行Blender操作"""
        # Blender可以通过Python API直接控制
        if action == "添加物体":
            object_type = params.get("type", "cube")
            return {
                "success": True,
                "api_call": f"bpy.ops.mesh.primitive_{object_type}_add()",
                "can_use_api": True,
                "visual_fallback": [
                    {"action": "click", "target": "添加菜单"},
                    {"action": "click", "target": "网格"},
                    {"action": "click", "target": object_type}
                ]
            }
        elif action == "选择物体":
            object_name = params.get("name")
            return {
                "success": True,
                "api_call": f"bpy.data.objects['{object_name}'].select_set(True)",
                "can_use_api": True
            }
        elif action == "渲染":
            return {
                "success": True,
                "api_call": "bpy.ops.render.render()",
                "can_use_api": True
            }
        
        return {"success": False, "error": f"Action {action} not implemented"}
    
    def get_element_hints(self) -> Dict[str, Dict]:
        return self.element_hints
    
    async def before_visual_action(self, action: str, params: Dict) -> bool:
        """优先使用API，必要时才用视觉"""
        # 如果提供了API调用，优先使用API
        if params.get("use_api"):
            return False  # 跳过视觉操作
        return True


# 全局实例
blender_adapter = BlenderAdapter()
