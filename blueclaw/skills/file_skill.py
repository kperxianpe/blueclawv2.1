# -*- coding: utf-8 -*-
"""File Skill - File system operations"""

from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Optional, List, Any

from .base_skill import BaseSkill, SkillResult, SkillParameter, PermissionLevel


class FileSkill(BaseSkill):
    """File system operations skill"""
    
    name = "file"
    description = "File system operations - read, write, search files"
    version = "1.0.0"
    permission_level = PermissionLevel.WRITE
    
    parameters = [
        SkillParameter("operation", "string", "Operation: read, write, append, delete, list, search", required=True),
        SkillParameter("path", "string", "File or directory path", required=True),
        SkillParameter("content", "string", "Content to write", required=False),
        SkillParameter("encoding", "string", "File encoding", required=False, default="utf-8"),
    ]
    
    async def execute(self, **kwargs) -> SkillResult:
        operation = kwargs.get('operation')
        path = kwargs.get('path')
        
        if not operation or not path:
            return SkillResult.fail(error="Missing required parameters: operation, path")
        
        try:
            if operation == 'read':
                return await self._read_file(path, kwargs.get('encoding', 'utf-8'))
            elif operation == 'write':
                return await self._write_file(path, kwargs.get('content', ''), kwargs.get('encoding', 'utf-8'))
            elif operation == 'list':
                return await self._list_directory(path)
            elif operation == 'delete':
                return await self._delete_file(path)
            else:
                return SkillResult.fail(error=f"Unknown operation: {operation}")
        except Exception as e:
            return SkillResult.fail(error=f"File operation failed: {str(e)}")
    
    async def _read_file(self, path: str, encoding: str) -> SkillResult:
        file_path = Path(path)
        if not file_path.exists():
            return SkillResult.fail(error=f"File not found: {path}")
        if file_path.is_dir():
            return SkillResult.fail(error=f"Path is a directory: {path}")
        
        content = file_path.read_text(encoding=encoding)
        
        if file_path.suffix == '.json':
            try:
                data = json.loads(content)
                return SkillResult.ok(data=data, metadata={'format': 'json'})
            except:
                pass
        
        if file_path.suffix == '.csv':
            try:
                lines = content.strip().split('\n')
                reader = csv.DictReader(lines)
                data = list(reader)
                return SkillResult.ok(data=data, metadata={'format': 'csv', 'rows': len(data)})
            except:
                pass
        
        return SkillResult.ok(data=content, metadata={'format': 'text', 'size': len(content)})
    
    async def _write_file(self, path: str, content: str, encoding: str) -> SkillResult:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(content, (dict, list)):
            content = json.dumps(content, indent=2, ensure_ascii=False)
        
        file_path.write_text(str(content), encoding=encoding)
        
        return SkillResult.ok(
            data=f"Written {len(str(content))} bytes to {path}",
            metadata={'path': str(file_path.absolute()), 'size': len(str(content))}
        )
    
    async def _list_directory(self, path: str) -> SkillResult:
        dir_path = Path(path)
        if not dir_path.exists():
            return SkillResult.fail(error=f"Directory not found: {path}")
        if not dir_path.is_dir():
            return SkillResult.fail(error=f"Path is not a directory: {path}")
        
        items = []
        for item in dir_path.iterdir():
            items.append({
                'name': item.name,
                'type': 'directory' if item.is_dir() else 'file',
                'size': item.stat().st_size if item.is_file() else None
            })
        
        return SkillResult.ok(
            data=items,
            metadata={'count': len(items), 'path': str(dir_path.absolute())}
        )
    
    async def _delete_file(self, path: str) -> SkillResult:
        file_path = Path(path)
        if not file_path.exists():
            return SkillResult.fail(error=f"Path not found: {path}")
        
        if file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        
        return SkillResult.ok(data=f"Deleted: {path}")
