#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映专业版适配器
"""
from typing import Dict, List
from .base import AppAdapter, AppState


class JianyingAdapter(AppAdapter):
    """剪映适配器"""
    
    def __init__(self):
        super().__init__("剪映专业版")
        
        # 剪映常见界面元素的位置提示（相对坐标，帮助VLM识别）
        self.element_hints = {
            "导入": {"region": "top_left", "color": ["white", "gray"]},
            "导出": {"region": "top_right", "color": ["orange", "red"]},
            "时间轴": {"region": "bottom", "height_percent": 0.3},
            "播放按钮": {"region": "center_bottom", "shape": "circle"},
            "轨道": {"region": "bottom", "pattern": "horizontal_stripes"},
            "素材库": {"region": "left", "width_percent": 0.2},
            "预览窗口": {"region": "center", "aspect_ratio": "16:9"},
        }
    
    async def detect_state(self) -> AppState:
        """检测剪映当前状态"""
        # 通过截图分析判断当前界面
        return AppState(
            app_name=self.app_name,
            is_running=True,
            current_view="main_editor",  # main_editor, export_dialog, settings, etc.
            available_actions=[
                "导入素材", "添加到轨道", "剪辑", "添加特效",
                "调整音频", "导出视频", "撤销", "重做"
            ],
            raw_state={}
        )
    
    async def execute_action(self, action: str, params: Dict) -> Dict:
        """执行剪映特定操作"""
        action_map = {
            "导入素材": self._action_import,
            "添加到轨道": self._action_add_to_timeline,
            "剪辑": self._action_cut,
            "导出视频": self._action_export,
        }
        
        handler = action_map.get(action)
        if handler:
            return await handler(params)
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    def get_element_hints(self) -> Dict[str, Dict]:
        return self.element_hints
    
    # ===== 具体动作实现 =====
    
    async def _action_import(self, params: Dict) -> Dict:
        """导入素材"""
        file_path = params.get("file_path")
        return {
            "success": True,
            "visual_steps": [
                {"action": "click", "target": "导入按钮"},
                {"action": "wait", "duration": 0.5},
                {"action": "type", "text": file_path},
                {"action": "click", "target": "确认按钮"}
            ]
        }
    
    async def _action_add_to_timeline(self, params: Dict) -> Dict:
        """添加到轨道"""
        material_name = params.get("material_name")
        track_index = params.get("track_index", 0)
        
        return {
            "success": True,
            "visual_steps": [
                {"action": "drag", "from": f"素材:{material_name}", "to": f"轨道{track_index}"}
            ]
        }
    
    async def _action_cut(self, params: Dict) -> Dict:
        """剪辑操作"""
        position = params.get("position")  # 时间轴位置
        
        return {
            "success": True,
            "visual_steps": [
                {"action": "click", "target": "时间轴", "position": position},
                {"action": "click", "target": "剪刀图标"}
            ]
        }
    
    async def _action_export(self, params: Dict) -> Dict:
        """导出视频"""
        return {
            "success": True,
            "visual_steps": [
                {"action": "click", "target": "导出按钮"},
                {"action": "wait", "duration": 1},
                {"action": "click", "target": "导出确认"}
            ]
        }


# 全局实例
jianying_adapter = JianyingAdapter()
