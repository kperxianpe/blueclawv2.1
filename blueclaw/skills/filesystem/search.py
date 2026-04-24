#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Search Skill

Search file contents with pattern matching.
"""

from pathlib import Path
import re
from typing import Optional, List
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class FileSearchSkill(Skill):
    name = "file_search"
    description = "搜索文件内容，支持正则表达式和全文搜索"
    category = "filesystem"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "搜索路径",
                "default": "."
            },
            "pattern": {
                "type": "string",
                "description": "搜索内容或正则表达式"
            },
            "file_pattern": {
                "type": "string",
                "description": "文件匹配模式，如 *.py",
                "default": "*"
            },
            "regex": {
                "type": "boolean",
                "default": False,
                "description": "是否使用正则表达式"
            },
            "case_sensitive": {
                "type": "boolean",
                "default": False,
                "description": "是否区分大小写"
            }
        },
        "required": ["pattern"]
    }
    
    capabilities = {
        "can_handle": ["文本搜索", "正则匹配", "代码搜索", "日志分析"],
        "cannot_handle": ["二进制文件搜索", "加密文件"],
        "typical_use_cases": [
            "在代码中查找函数",
            "搜索日志中的错误",
            "查找配置文件设置",
            "批量文本替换预览"
        ]
    }
    
    examples = [
        {
            "description": "搜索Python文件中的TODO",
            "input": {"pattern": "TODO", "file_pattern": "*.py"},
            "output": "Found in file1.py:12, file2.py:45..."
        },
        {
            "description": "使用正则搜索函数定义",
            "input": {"pattern": r"def \w+_", "file_pattern": "*.py", "regex": True},
            "output": "Found matches..."
        }
    ]
    
    async def execute(self, pattern: str, path: str = ".", 
                     file_pattern: str = "*", regex: bool = False,
                     case_sensitive: bool = False) -> SkillResult:
        search_path = Path(path)
        
        try:
            if not search_path.exists():
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"路径不存在: {path}"
                )
            
            # Compile regex if needed
            if regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                try:
                    compiled_pattern = re.compile(pattern, flags)
                except re.error as e:
                    return SkillResult(
                        success=False,
                        output=None,
                        error_message=f"无效的正则表达式: {e}"
                    )
            else:
                search_text = pattern if case_sensitive else pattern.lower()
            
            # Search files
            results = []
            files_searched = 0
            
            for file_path in search_path.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                
                # Skip binary files
                if self._is_binary(file_path):
                    continue
                
                files_searched += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            match = False
                            
                            if regex:
                                if compiled_pattern.search(line):
                                    match = True
                            else:
                                line_text = line if case_sensitive else line.lower()
                                if search_text in line_text:
                                    match = True
                            
                            if match:
                                results.append({
                                    "file": str(file_path.relative_to(search_path)),
                                    "line": line_num,
                                    "content": line.rstrip('\n\r'),
                                    "full_path": str(file_path.absolute())
                                })
                                
                                # Limit results per file
                                if len([r for r in results if r["file"] == str(file_path.relative_to(search_path))]) >= 100:
                                    break
                                    
                except (PermissionError, OSError):
                    continue
                
                # Limit total files
                if files_searched >= 1000:
                    break
            
            return SkillResult(
                success=True,
                output={
                    "matches": results[:500],  # Limit total results
                    "total_matches": len(results),
                    "files_searched": files_searched
                },
                metadata={
                    "pattern": pattern,
                    "regex": regex,
                    "case_sensitive": case_sensitive,
                    "file_pattern": file_pattern
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
    
    def _is_binary(self, file_path: Path, sample_size: int = 1024) -> bool:
        """Check if file is binary"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(sample_size)
                return b'\0' in chunk
        except:
            return True
