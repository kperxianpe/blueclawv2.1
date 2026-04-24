# -*- coding: utf-8 -*-
"""
Web Adapter 数据模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WebElement(BaseModel):
    """网页可交互元素"""
    id: str
    tag: str
    element_type: str = "other"  # button/input/link/select/textarea/other
    text: str = ""
    aria_label: str = ""
    placeholder: str = ""
    title: str = ""
    selector: str = ""
    xpath: str = ""
    bbox: Dict[str, float] = Field(default_factory=dict)  # x, y, width, height (px)
    normalized_coords: Dict[str, float] = Field(default_factory=dict)  # 0-1
    is_visible: bool = True
    is_distraction: bool = False
    z_index: int = 0
    position: str = ""
    attributes: Dict[str, Any] = Field(default_factory=dict)


class PageAnalysis(BaseModel):
    """页面分析结果"""
    url: str = ""
    title: str = ""
    timestamp: float = 0.0
    screenshot: bytes = b""
    elements: List[WebElement] = Field(default_factory=list)
    distractions: List[WebElement] = Field(default_factory=list)
    viewport_width: int = 0
    viewport_height: int = 0


class LocationResult(BaseModel):
    """元素定位结果"""
    found: bool = False
    strategy: str = ""  # semantic/selector/coordinate/fallback
    element: Optional[WebElement] = None
    fallback_reason: Optional[str] = None
