#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Read Skill

Read text file contents with encoding auto-detection and line limits.
"""

from pathlib import Path
from typing import Optional
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class FileReadSkill(Skill):
    name = "file_read"
    description = "读取文本文件内容，支持编码自动检测和行数限制"
    category = "filesystem"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径，支持相对路径和绝对路径"
            },
            "encoding": {
                "type": "string",
                "enum": ["utf-8", "gbk", "latin-1", "auto"],
                "default": "utf-8",
                "description": "文件编码，auto 表示自动检测"
            },
            "limit_lines": {
                "type": "integer",
                "description": "限制读取行数，用于大文件预览",
                "minimum": 1
            }
        },
        "required": ["path"]
    }
    
    capabilities = {
        "can_handle": ["文本文件", "代码文件", "配置文件", "日志文件", "JSON", "CSV"],
        "cannot_handle": ["二进制可执行文件", "加密文件", "图片", "视频"],
        "typical_use_cases": [
            "查看代码文件内容",
            "读取配置文件参数",
            "分析日志文件错误",
            "预览大文件前N行"
        ]
    }
    
    examples = [
        {
            "description": "读取 README 文件",
            "input": {"path": "README.md"},
            "output": "# Project Name\n\nThis is a sample project..."
        },
        {
            "description": "预览代码前50行",
            "input": {"path": "app.py", "limit_lines": 50},
            "output": "import os\nimport sys\n..."
        }
    ]
    
    async def execute(self, path: str, encoding: str = "utf-8",
                     limit_lines: int = None) -> SkillResult:
        file_path = Path(path)
        
        try:
            # Check existence
            if not file_path.exists():
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"文件不存在: {path}"
                )
            
            # Check if it's a file
            if not file_path.is_file():
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"路径不是文件: {path}"
                )
            
            # Auto-detect encoding
            if encoding == "auto":
                encoding = self._detect_encoding(file_path)
            
            # Read file
            with open(file_path, 'r', encoding=encoding) as f:
                if limit_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= limit_lines:
                            break
                        lines.append(line)
                    content = ''.join(lines)
                    truncated = True
                    total_lines = i + 1
                else:
                    content = f.read()
                    truncated = False
                    total_lines = content.count('\n') + 1
            
            return SkillResult(
                success=True,
                output=content,
                metadata={
                    "path": str(file_path.absolute()),
                    "encoding": encoding,
                    "lines": total_lines,
                    "truncated": truncated,
                    "size_bytes": file_path.stat().st_size
                }
            )
            
        except UnicodeDecodeError as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"无法使用 {encoding} 编码读取文件: {e}",
                suggestion="尝试使用 encoding='latin-1' 参数"
            )
        except PermissionError as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"权限不足: {e}",
                suggestion="检查文件权限，或使用管理员权限运行"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
    
    def _detect_encoding(self, file_path: Path) -> str:
        """Simple encoding detection"""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read(10000))
                return result.get('encoding', 'utf-8')
        except ImportError:
            # Fallback: try common encodings
            for enc in ['utf-8', 'gbk', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        f.read(100)
                    return enc
                except UnicodeDecodeError:
                    continue
            return 'utf-8'
