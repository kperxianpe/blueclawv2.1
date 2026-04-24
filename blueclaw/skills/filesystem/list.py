#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File List Skill

List directory contents with filtering options.
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class FileListSkill(Skill):
    name = "file_list"
    description = "列出目录内容，支持过滤和递归"
    category = "filesystem"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "目录路径",
                "default": "."
            },
            "pattern": {
                "type": "string",
                "description": "文件名匹配模式，如 *.py",
                "default": "*"
            },
            "recursive": {
                "type": "boolean",
                "default": False,
                "description": "是否递归列出子目录"
            },
            "include_hidden": {
                "type": "boolean",
                "default": False,
                "description": "是否包含隐藏文件"
            }
        },
        "required": []
    }
    
    capabilities = {
        "can_handle": ["目录遍历", "文件过滤", "文件统计"],
        "cannot_handle": ["权限不足的目录", "系统保护目录"],
        "typical_use_cases": [
            "查看项目结构",
            "查找特定类型文件",
            "统计文件数量",
            "检查目录内容"
        ]
    }
    
    examples = [
        {
            "description": "列出当前目录",
            "input": {},
            "output": "dir1, dir2, file1.txt, file2.py..."
        },
        {
            "description": "递归列出所有Python文件",
            "input": {"pattern": "*.py", "recursive": True},
            "output": "src/main.py, src/utils.py..."
        }
    ]
    
    async def execute(self, path: str = ".", pattern: str = "*",
                     recursive: bool = False, include_hidden: bool = False) -> SkillResult:
        dir_path = Path(path)
        
        try:
            if not dir_path.exists():
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"目录不存在: {path}"
                )
            
            if not dir_path.is_dir():
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"路径不是目录: {path}"
                )
            
            # List files
            if recursive:
                files = list(dir_path.rglob(pattern))
            else:
                files = list(dir_path.glob(pattern))
            
            # Filter hidden files
            if not include_hidden:
                files = [f for f in files if not f.name.startswith('.')]
            
            # Build result
            items = []
            for f in files:
                try:
                    stat = f.stat()
                    items.append({
                        "name": f.name,
                        "path": str(f.relative_to(dir_path)),
                        "type": "directory" if f.is_dir() else "file",
                        "size": stat.st_size if f.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except (OSError, PermissionError):
                    # Skip files we can't stat
                    items.append({
                        "name": f.name,
                        "path": str(f.relative_to(dir_path)),
                        "type": "unknown",
                        "size": None,
                        "modified": None
                    })
            
            # Sort: directories first, then by name
            items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"]))
            
            return SkillResult(
                success=True,
                output={
                    "path": str(dir_path.absolute()),
                    "items": items,
                    "count": len(items),
                    "files": sum(1 for i in items if i["type"] == "file"),
                    "directories": sum(1 for i in items if i["type"] == "directory")
                },
                metadata={
                    "pattern": pattern,
                    "recursive": recursive,
                    "include_hidden": include_hidden
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
