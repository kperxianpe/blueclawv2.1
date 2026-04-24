#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VMS - Visual Memory System
视觉记忆系统：截图捕获、存储、管理
"""
import base64
import io
import os
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import uuid

try:
    from PIL import Image
    import pyautogui
    VMS_AVAILABLE = True
except ImportError:
    VMS_AVAILABLE = False


@dataclass
class Screenshot:
    """截图对象"""
    id: str
    task_id: str
    image_data: bytes  # PNG bytes
    width: int
    height: int
    region: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    timestamp: float = field(default_factory=time.time)
    annotations: List[Dict] = field(default_factory=list)  # 标注信息
    
    @property
    def base64(self) -> str:
        """获取 base64 编码（用于前端展示）"""
        return base64.b64encode(self.image_data).decode('utf-8')
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "width": self.width,
            "height": self.height,
            "region": self.region,
            "timestamp": self.timestamp,
            "base64_preview": self.base64[:100] + "..." if len(self.base64) > 100 else self.base64,
            "annotations": self.annotations
        }


class VisualMemorySystem:
    """
    视觉记忆系统
    - 全屏/区域截图
    - 截图存储与检索
    - 截图标注
    """
    
    def __init__(self, storage_dir: str = "./screenshots"):
        self.storage_dir = storage_dir
        self.screenshots: Dict[str, Screenshot] = {}
        os.makedirs(storage_dir, exist_ok=True)
        
        if not VMS_AVAILABLE:
            print("[VMS] Warning: PIL/pyautogui not available, using mock mode")
    
    async def capture_fullscreen(self, task_id: str) -> Optional[Screenshot]:
        """
        捕获全屏截图
        返回: Screenshot 对象
        """
        if not VMS_AVAILABLE:
            return await self._mock_screenshot(task_id)
        
        try:
            # 使用 pyautogui 截图
            screenshot = pyautogui.screenshot()
            
            # 转换为 PNG bytes
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            
            screenshot_obj = Screenshot(
                id=f"ss_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                image_data=image_data,
                width=screenshot.width,
                height=screenshot.height,
                region=None
            )
            
            self.screenshots[screenshot_obj.id] = screenshot_obj
            await self._save_to_disk(screenshot_obj)
            
            print(f"[VMS] Fullscreen captured: {screenshot_obj.id} ({screenshot.width}x{screenshot.height})")
            return screenshot_obj
            
        except Exception as e:
            print(f"[VMS] Capture failed: {e}")
            return None
    
    async def capture_region(
        self,
        task_id: str,
        x: int,
        y: int,
        width: int,
        height: int
    ) -> Optional[Screenshot]:
        """
        捕获指定区域截图
        参数:
            x, y: 左上角坐标
            width, height: 宽高
        """
        if not VMS_AVAILABLE:
            return await self._mock_screenshot(task_id, region=(x, y, width, height))
        
        try:
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            
            screenshot_obj = Screenshot(
                id=f"ss_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                image_data=image_data,
                width=width,
                height=height,
                region=(x, y, width, height)
            )
            
            self.screenshots[screenshot_obj.id] = screenshot_obj
            await self._save_to_disk(screenshot_obj)
            
            print(f"[VMS] Region captured: {screenshot_obj.id} ({width}x{height} @ {x},{y})")
            return screenshot_obj
            
        except Exception as e:
            print(f"[VMS] Region capture failed: {e}")
            return None
    
    async def capture_around_point(
        self,
        task_id: str,
        x: int,
        y: int,
        radius: int = 200
    ) -> Optional[Screenshot]:
        """
        捕获指定点周围的区域（用于详细查看某个元素）
        """
        x1 = max(0, x - radius)
        y1 = max(0, y - radius)
        width = radius * 2
        height = radius * 2
        
        return await self.capture_region(task_id, x1, y1, width, height)
    
    def get_screenshot(self, screenshot_id: str) -> Optional[Screenshot]:
        """获取截图"""
        return self.screenshots.get(screenshot_id)
    
    def get_task_screenshots(self, task_id: str) -> List[Screenshot]:
        """获取任务的所有截图"""
        return [ss for ss in self.screenshots.values() if ss.task_id == task_id]
    
    def add_annotation(
        self,
        screenshot_id: str,
        annotation_type: str,  # "circle", "rect", "arrow", "text"
        coordinates: Dict,
        label: Optional[str] = None,
        color: str = "#FF6B35"
    ):
        """
        添加截图标注
        coordinates: {"x": int, "y": int, "width": int, "height": int} 或 {"x1", "y1", "x2", "y2"}
        """
        screenshot = self.screenshots.get(screenshot_id)
        if not screenshot:
            return False
        
        annotation = {
            "id": f"ann_{uuid.uuid4().hex[:6]}",
            "type": annotation_type,
            "coordinates": coordinates,
            "label": label,
            "color": color,
            "timestamp": time.time()
        }
        
        screenshot.annotations.append(annotation)
        return True
    
    async def _save_to_disk(self, screenshot: Screenshot):
        """保存截图到磁盘"""
        filepath = os.path.join(self.storage_dir, f"{screenshot.id}.png")
        with open(filepath, 'wb') as f:
            f.write(screenshot.image_data)
    
    async def _mock_screenshot(self, task_id: str, region: Optional[Tuple] = None) -> Screenshot:
        """模拟截图（用于测试环境）"""
        import asyncio
        
        if VMS_AVAILABLE:
            # 创建测试图片
            img = Image.new('RGB', (1920, 1080) if not region else (region[2], region[3]), color=(100, 150, 200))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_data = buffer.getvalue()
        else:
            # 无 PIL 时返回空数据
            img_data = b"mock_image_data"
        
        return Screenshot(
            id=f"ss_mock_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            image_data=img_data,
            width=1920 if not region else region[2],
            height=1080 if not region else region[3],
            region=region
        )


# 全局 VMS 实例
vms = VisualMemorySystem()
