#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MPL - Motor Primitive Library
动作原语库：鼠标、键盘、系统操作
"""
import time
import asyncio
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # 鼠标移到左上角停止
    pyautogui.PAUSE = 0.1
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False


class ActionType(Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    SCROLL = "scroll"
    TYPE = "type"
    KEYPRESS = "keypress"
    HOVER = "hover"
    WAIT = "wait"


@dataclass
class ActionResult:
    """动作执行结果"""
    success: bool
    action_type: str
    coordinates: Optional[Tuple[int, int]]
    message: str
    duration_ms: float
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "action_type": self.action_type,
            "coordinates": self.coordinates,
            "message": self.message,
            "duration_ms": self.duration_ms
        }


class MotorPrimitiveLibrary:
    """
    动作原语库
    所有操作都返回 ActionResult，包含执行结果和耗时
    """
    
    def __init__(self):
        self.last_position = (0, 0)
        if not MPL_AVAILABLE:
            print("[MPL] Warning: pyautogui not available, using mock mode")
    
    async def click(self, x: int, y: int, duration: float = 0.5) -> ActionResult:
        """单击指定位置"""
        start = time.time()
        
        if MPL_AVAILABLE:
            try:
                pyautogui.moveTo(x, y, duration=duration)
                pyautogui.click()
                self.last_position = (x, y)
                
                return ActionResult(
                    success=True,
                    action_type="click",
                    coordinates=(x, y),
                    message=f"Clicked at ({x}, {y})",
                    duration_ms=(time.time() - start) * 1000
                )
            except Exception as e:
                return ActionResult(
                    success=False,
                    action_type="click",
                    coordinates=(x, y),
                    message=f"Failed: {e}",
                    duration_ms=(time.time() - start) * 1000
                )
        else:
            await asyncio.sleep(0.1)
            self.last_position = (x, y)
            return ActionResult(
                success=True,
                action_type="click",
                coordinates=(x, y),
                message=f"[MOCK] Clicked at ({x}, {y})",
                duration_ms=100
            )
    
    async def double_click(self, x: int, y: int, duration: float = 0.5) -> ActionResult:
        """双击"""
        start = time.time()
        
        if MPL_AVAILABLE:
            pyautogui.moveTo(x, y, duration=duration)
            pyautogui.doubleClick()
        else:
            await asyncio.sleep(0.1)
        
        self.last_position = (x, y)
        return ActionResult(
            success=True,
            action_type="double_click",
            coordinates=(x, y),
            message=f"Double-clicked at ({x}, {y})",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def right_click(self, x: int, y: int, duration: float = 0.5) -> ActionResult:
        """右键单击"""
        start = time.time()
        
        if MPL_AVAILABLE:
            pyautogui.moveTo(x, y, duration=duration)
            pyautogui.rightClick()
        else:
            await asyncio.sleep(0.1)
        
        self.last_position = (x, y)
        return ActionResult(
            success=True,
            action_type="right_click",
            coordinates=(x, y),
            message=f"Right-clicked at ({x}, {y})",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5
    ) -> ActionResult:
        """拖拽"""
        start = time.time()
        
        if MPL_AVAILABLE:
            pyautogui.moveTo(start_x, start_y, duration=0.2)
            pyautogui.dragTo(end_x, end_y, duration=duration)
        else:
            await asyncio.sleep(duration)
        
        self.last_position = (end_x, end_y)
        return ActionResult(
            success=True,
            action_type="drag",
            coordinates=(end_x, end_y),
            message=f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> ActionResult:
        """
        滚动
        amount: 正数向上，负数向下
        """
        start = time.time()
        
        if MPL_AVAILABLE:
            if x is not None and y is not None:
                pyautogui.scroll(amount, x, y)
            else:
                pyautogui.scroll(amount)
        else:
            await asyncio.sleep(0.1)
        
        return ActionResult(
            success=True,
            action_type="scroll",
            coordinates=(x, y) if x else self.last_position,
            message=f"Scrolled {amount}",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def type_text(self, text: str, interval: float = 0.01) -> ActionResult:
        """输入文字"""
        start = time.time()
        
        if MPL_AVAILABLE:
            pyautogui.typewrite(text, interval=interval)
        else:
            await asyncio.sleep(len(text) * 0.01)
        
        return ActionResult(
            success=True,
            action_type="type",
            coordinates=self.last_position,
            message=f"Typed: {text[:20]}..." if len(text) > 20 else f"Typed: {text}",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def keypress(self, keys: list) -> ActionResult:
        """
        按键组合
        keys: ["ctrl", "c"] 或 ["enter"]
        """
        start = time.time()
        
        if MPL_AVAILABLE:
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
        else:
            await asyncio.sleep(0.1)
        
        return ActionResult(
            success=True,
            action_type="keypress",
            coordinates=self.last_position,
            message=f"Pressed: {'+'.join(keys)}",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def hover(self, x: int, y: int, duration: float = 0.5) -> ActionResult:
        """悬停"""
        start = time.time()
        
        if MPL_AVAILABLE:
            pyautogui.moveTo(x, y, duration=duration)
        else:
            await asyncio.sleep(duration)
        
        self.last_position = (x, y)
        return ActionResult(
            success=True,
            action_type="hover",
            coordinates=(x, y),
            message=f"Hovered at ({x}, {y})",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def wait(self, seconds: float) -> ActionResult:
        """等待"""
        start = time.time()
        await asyncio.sleep(seconds)
        
        return ActionResult(
            success=True,
            action_type="wait",
            coordinates=self.last_position,
            message=f"Waited {seconds}s",
            duration_ms=(time.time() - start) * 1000
        )
    
    async def execute_action(self, action_def: dict) -> ActionResult:
        """
        根据动作定义执行
        action_def: {"action": "click", "x": 100, "y": 200, ...}
        """
        action_type = action_def.get("action")
        
        if action_type == "click":
            return await self.click(
                action_def.get("x", 0),
                action_def.get("y", 0),
                action_def.get("duration", 0.5)
            )
        elif action_type == "double_click":
            return await self.double_click(
                action_def.get("x", 0),
                action_def.get("y", 0)
            )
        elif action_type == "right_click":
            return await self.right_click(
                action_def.get("x", 0),
                action_def.get("y", 0)
            )
        elif action_type == "drag":
            return await self.drag(
                action_def.get("start_x", 0),
                action_def.get("start_y", 0),
                action_def.get("end_x", 0),
                action_def.get("end_y", 0),
                action_def.get("duration", 0.5)
            )
        elif action_type == "scroll":
            return await self.scroll(
                action_def.get("amount", 0),
                action_def.get("x"),
                action_def.get("y")
            )
        elif action_type == "type":
            return await self.type_text(
                action_def.get("text", ""),
                action_def.get("interval", 0.01)
            )
        elif action_type == "keypress":
            return await self.keypress(action_def.get("keys", []))
        elif action_type == "hover":
            return await self.hover(
                action_def.get("x", 0),
                action_def.get("y", 0)
            )
        elif action_type == "wait":
            return await self.wait(action_def.get("duration", 0.5))
        else:
            return ActionResult(
                success=False,
                action_type="unknown",
                coordinates=self.last_position,
                message=f"Unknown action: {action_type}",
                duration_ms=0
            )


# 全局 MPL 实例
mpl = MotorPrimitiveLibrary()
