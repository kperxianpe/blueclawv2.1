#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Parse Skill

Parse structured data formats like JSON, CSV, XML.
"""

import json
import csv
from io import StringIO
from pathlib import Path
from typing import Optional, Union, Dict, List, Any
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class DataParseSkill(Skill):
    name = "data_parse"
    description = "解析结构化数据（JSON, CSV, XML）"
    category = "data"
    
    parameters = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "数据源：文件路径或直接内容"
            },
            "format": {
                "type": "string",
                "enum": ["json", "csv", "xml", "auto"],
                "default": "auto",
                "description": "数据格式"
            },
            "is_path": {
                "type": "boolean",
                "default": True,
                "description": "source是否为文件路径"
            },
            "csv_delimiter": {
                "type": "string",
                "default": ",",
                "description": "CSV分隔符"
            },
            "csv_has_header": {
                "type": "boolean",
                "default": True,
                "description": "CSV是否包含表头"
            }
        },
        "required": ["source"]
    }
    
    capabilities = {
        "can_handle": ["JSON", "CSV", "简单XML", "嵌套结构"],
        "cannot_handle": ["二进制格式", "复杂XML命名空间", "加密数据"],
        "typical_use_cases": [
            "解析配置文件",
            "读取数据表",
            "处理API响应",
            "数据导入"
        ]
    }
    
    examples = [
        {
            "description": "解析JSON文件",
            "input": {"source": "data.json", "format": "json"},
            "output": {"name": "test", "value": 123}
        },
        {
            "description": "解析CSV字符串",
            "input": {"source": "a,b,c\n1,2,3", "format": "csv", "is_path": False},
            "output": [{"a": "1", "b": "2", "c": "3"}]
        }
    ]
    
    async def execute(self, source: str, format: str = "auto",
                     is_path: bool = True, csv_delimiter: str = ",",
                     csv_has_header: bool = True) -> SkillResult:
        # Get content
        if is_path:
            file_path = Path(source)
            if not file_path.exists():
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"文件不存在: {source}"
                )
            try:
                content = file_path.read_text(encoding='utf-8')
            except Exception as e:
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"读取文件失败: {e}"
                )
            # Auto-detect format from extension
            if format == "auto":
                format = self._detect_format(file_path.suffix)
        else:
            content = source
            # Auto-detect format from content
            if format == "auto":
                format = self._detect_format_from_content(content)
        
        # Parse based on format
        try:
            if format == "json":
                result = self._parse_json(content)
            elif format == "csv":
                result = self._parse_csv(content, csv_delimiter, csv_has_header)
            elif format == "xml":
                result = self._parse_xml(content)
            else:
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"不支持的格式: {format}",
                    suggestion="支持的格式: json, csv, xml"
                )
            
            return SkillResult(
                success=True,
                output=result,
                metadata={
                    "format": format,
                    "source_type": "path" if is_path else "inline",
                    "size_bytes": len(content.encode('utf-8'))
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"解析失败: {e}",
                suggestion=f"检查{format.upper()}格式是否正确"
            )
    
    def _detect_format(self, suffix: str) -> str:
        """Detect format from file extension"""
        ext_map = {
            '.json': 'json',
            '.csv': 'csv',
            '.xml': 'xml',
            '.yaml': 'json',  # Could use yaml parser
            '.yml': 'json',
        }
        return ext_map.get(suffix.lower(), 'json')
    
    def _detect_format_from_content(self, content: str) -> str:
        """Detect format from content"""
        content = content.strip()
        if content.startswith(('{', '[')):
            return 'json'
        if content.startswith('<'):
            return 'xml'
        if ',' in content.split('\n')[0]:
            return 'csv'
        return 'json'
    
    def _parse_json(self, content: str) -> Any:
        """Parse JSON"""
        return json.loads(content)
    
    def _parse_csv(self, content: str, delimiter: str, has_header: bool) -> List[Dict]:
        """Parse CSV"""
        reader = csv.reader(StringIO(content), delimiter=delimiter)
        rows = list(reader)
        
        if not rows:
            return []
        
        if has_header:
            headers = rows[0]
            data_rows = rows[1:]
        else:
            headers = [f"col_{i}" for i in range(len(rows[0]))]
            data_rows = rows
        
        return [
            {headers[i]: value for i, value in enumerate(row)}
            for row in data_rows
        ]
    
    def _parse_xml(self, content: str) -> Dict:
        """Parse simple XML"""
        # Simple XML parsing (for production, use xml.etree or lxml)
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(content)
        
        def element_to_dict(element):
            result = {
                "tag": element.tag,
                "text": element.text.strip() if element.text else None,
                "attrib": dict(element.attrib),
                "children": [element_to_dict(child) for child in element]
            }
            return result
        
        return element_to_dict(root)
