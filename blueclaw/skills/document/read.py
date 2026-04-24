#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Read Skill

Read document files (simple text-based formats).
"""

from pathlib import Path
from typing import Optional
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class DocReadSkill(Skill):
    name = "doc_read"
    description = "读取文档内容（支持txt, md, html等文本格式）"
    category = "document"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文档文件路径"
            },
            "encoding": {
                "type": "string",
                "default": "utf-8",
                "description": "文件编码"
            }
        },
        "required": ["path"]
    }
    
    capabilities = {
        "can_handle": ["TXT", "MD", "HTML", "CSV", "JSON"],
        "cannot_handle": ["DOCX", "PDF", "XLSX", "二进制文档"],
        "typical_use_cases": [
            "读取文本文档",
            "查看Markdown文件",
            "提取文档内容"
        ]
    }
    
    examples = [
        {
            "description": "读取文档",
            "input": {"path": "readme.md"},
            "output": "# Title\nContent..."
        }
    ]
    
    async def execute(self, path: str, encoding: str = "utf-8") -> SkillResult:
        file_path = Path(path)
        
        if not file_path.exists():
            return SkillResult(
                success=False,
                output=None,
                error_message=f"文件不存在: {path}"
            )
        
        # Check supported extensions
        ext = file_path.suffix.lower()
        supported = ['.txt', '.md', '.markdown', '.html', '.htm', '.csv', '.json', '.xml', '.yaml', '.yml', '.rst']
        
        if ext not in supported:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"不支持的文档格式: {ext}",
                suggestion=f"支持的格式: {', '.join(supported)}"
            )
        
        try:
            content = file_path.read_text(encoding=encoding)
            
            return SkillResult(
                success=True,
                output=content,
                metadata={
                    "path": str(file_path.absolute()),
                    "format": ext,
                    "size": len(content),
                    "lines": content.count('\n') + 1
                }
            )
            
        except UnicodeDecodeError:
            return SkillResult(
                success=False,
                output=None,
                error_message="解码失败",
                suggestion="尝试其他编码如 'latin-1' 或 'gbk'"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
