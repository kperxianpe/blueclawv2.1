#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Write Skill

Write document files (simple text-based formats).
"""

from pathlib import Path
from typing import Optional
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class DocWriteSkill(Skill):
    name = "doc_write"
    description = "写入文档内容（支持txt, md, html等文本格式）"
    category = "document"
    dangerous = True
    dangerous_level = 1  # Notify before execution
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文档文件路径"
            },
            "content": {
                "type": "string",
                "description": "文档内容"
            },
            "encoding": {
                "type": "string",
                "default": "utf-8",
                "description": "文件编码"
            },
            "backup": {
                "type": "boolean",
                "default": True,
                "description": "是否备份原文件"
            }
        },
        "required": ["path", "content"]
    }
    
    capabilities = {
        "can_handle": ["TXT", "MD", "HTML", "代码文档"],
        "cannot_handle": ["DOCX", "PDF", "XLSX", "二进制文档"],
        "typical_use_cases": [
            "创建文本文档",
            "生成Markdown",
            "保存报告"
        ]
    }
    
    examples = [
        {
            "description": "写入Markdown文件",
            "input": {"path": "report.md", "content": "# Report\n\nContent..."},
            "output": "文档写入成功"
        }
    ]
    
    async def execute(self, path: str, content: str, 
                     encoding: str = "utf-8", backup: bool = True) -> SkillResult:
        file_path = Path(path)
        
        # Validate extension
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
            # Create directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file
            if file_path.exists() and backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                backup_path.write_bytes(file_path.read_bytes())
            
            # Write file
            file_path.write_text(content, encoding=encoding)
            
            return SkillResult(
                success=True,
                output=f"文档已写入: {file_path}",
                metadata={
                    "path": str(file_path.absolute()),
                    "format": ext,
                    "size": len(content),
                    "backup_created": backup and file_path.with_suffix(file_path.suffix + ".backup").exists()
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
