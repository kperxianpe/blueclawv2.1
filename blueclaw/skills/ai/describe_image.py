#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Describe Image Skill

Image description using basic image analysis (placeholder for vision API).
"""

from pathlib import Path
from typing import Optional, Dict
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class AIDescribeImageSkill(Skill):
    name = "ai_describe_image"
    description = "描述图片内容（演示模式，生产环境接入视觉API）"
    category = "ai"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "图片文件路径"
            },
            "detail_level": {
                "type": "string",
                "enum": ["basic", "detailed"],
                "default": "basic",
                "description": "描述详细程度"
            }
        },
        "required": ["path"]
    }
    
    capabilities = {
        "can_handle": ["常见图片格式", "照片", "截图"],
        "cannot_handle": ["模糊图片", "艺术画", "复杂场景分析"],
        "typical_use_cases": [
            "获取图片描述",
            "分析图片属性",
            "图片预览信息"
        ]
    }
    
    examples = [
        {
            "description": "描述图片",
            "input": {"path": "photo.jpg"},
            "output": "这是一张尺寸为1920x1080的JPEG图片..."
        }
    ]
    
    async def execute(self, path: str, detail_level: str = "basic") -> SkillResult:
        file_path = Path(path)
        
        if not file_path.exists():
            return SkillResult(
                success=False,
                output=None,
                error_message=f"文件不存在: {path}"
            )
        
        try:
            # Try to use PIL for basic info
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    width, height = img.size
                    format_name = img.format or "Unknown"
                    mode = img.mode
                    
                    description = (
                        f"这是一张 {width}x{height} 像素的 {format_name} 图片，"
                        f"颜色模式为 {mode}。"
                    )
                    
                    metadata = {
                        "width": width,
                        "height": height,
                        "format": format_name,
                        "mode": mode,
                        "file_size": file_path.stat().st_size
                    }
            except ImportError:
                # Fallback: just file info
                description = f"图片文件: {file_path.name}"
                metadata = {
                    "file_size": file_path.stat().st_size,
                    "note": "PIL not available, limited information"
                }
            
            return SkillResult(
                success=True,
                output=description,
                metadata={
                    "path": str(file_path.absolute()),
                    "detail_level": detail_level,
                    **metadata,
                    "note": "演示模式 - 生产环境请接入视觉API获取详细描述"
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
