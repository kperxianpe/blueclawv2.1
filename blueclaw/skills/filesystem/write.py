#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Write Skill

Write content to files with safety checks.
"""

from pathlib import Path
from typing import Optional, Union
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class FileWriteSkill(Skill):
    name = "file_write"
    description = "写入内容到文件，支持自动创建目录和备份"
    category = "filesystem"
    dangerous = True
    dangerous_level = 1  # Will notify user before execution
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径"
            },
            "content": {
                "type": "string",
                "description": "要写入的内容"
            },
            "encoding": {
                "type": "string",
                "default": "utf-8",
                "description": "文件编码"
            },
            "append": {
                "type": "boolean",
                "default": False,
                "description": "是否追加模式"
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
        "can_handle": ["文本写入", "配置文件生成", "代码生成", "日志写入"],
        "cannot_handle": ["二进制数据", "流式写入"],
        "typical_use_cases": [
            "生成配置文件",
            "保存代码输出",
            "写入日志记录",
            "创建新文件"
        ]
    }
    
    examples = [
        {
            "description": "创建配置文件",
            "input": {"path": "config.json", "content": '{"name": "test"}'},
            "output": "文件写入成功"
        },
        {
            "description": "追加日志",
            "input": {"path": "app.log", "content": "New log entry", "append": True},
            "output": "内容追加成功"
        }
    ]
    
    async def execute(self, path: str, content: str, encoding: str = "utf-8",
                     append: bool = False, backup: bool = True) -> SkillResult:
        file_path = Path(path)
        
        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file
            if file_path.exists() and backup and not append:
                backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                backup_path.write_bytes(file_path.read_bytes())
            
            # Write file
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            return SkillResult(
                success=True,
                output=f"{'追加到' if append else '写入'}: {file_path}",
                metadata={
                    "path": str(file_path.absolute()),
                    "bytes_written": len(content.encode(encoding)),
                    "backup_created": file_path.with_suffix(file_path.suffix + ".backup").exists() if file_path.exists() and backup and not append else False
                }
            )
            
        except PermissionError as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"权限不足: {e}",
                suggestion="检查目录权限，或使用管理员权限运行"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
