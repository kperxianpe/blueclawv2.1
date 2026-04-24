#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Transform Skill

Transform data between formats and apply operations.
"""

import json
from typing import Any, Dict, List, Optional
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class DataTransformSkill(Skill):
    name = "data_transform"
    description = "数据转换和清洗（格式转换、过滤、排序）"
    category = "data"
    
    parameters = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "输入数据"
            },
            "operation": {
                "type": "string",
                "enum": ["filter", "sort", "map", "flatten", "group", "convert"],
                "description": "操作类型"
            },
            "config": {
                "type": "object",
                "description": "操作配置"
            },
            "output_format": {
                "type": "string",
                "enum": ["json", "csv", "list"],
                "default": "json",
                "description": "输出格式"
            }
        },
        "required": ["data", "operation"]
    }
    
    capabilities = {
        "can_handle": ["列表处理", "字典处理", "数据过滤", "数据排序", "格式转换"],
        "cannot_handle": ["二进制数据", "流式处理", "复杂聚合"],
        "typical_use_cases": [
            "数据清洗",
            "格式转换",
            "列表排序",
            "字段提取",
            "数据合并"
        ]
    }
    
    examples = [
        {
            "description": "过滤列表",
            "input": {
                "data": {"items": [{"age": 20}, {"age": 30}]},
                "operation": "filter",
                "config": {"field": "age", "min": 25}
            },
            "output": [{"age": 30}]
        },
        {
            "description": "按字段排序",
            "input": {
                "data": {"records": [{"name": "B"}, {"name": "A"}]},
                "operation": "sort",
                "config": {"field": "name"}
            },
            "output": [{"name": "A"}, {"name": "B"}]
        }
    ]
    
    async def execute(self, data: Any, operation: str,
                     config: Dict = None, output_format: str = "json") -> SkillResult:
        config = config or {}
        
        try:
            # Extract data if wrapped
            if isinstance(data, dict) and "items" in data:
                input_data = data["items"]
            elif isinstance(data, dict) and "records" in data:
                input_data = data["records"]
            else:
                input_data = data
            
            # Execute operation
            if operation == "filter":
                result = self._filter(input_data, config)
            elif operation == "sort":
                result = self._sort(input_data, config)
            elif operation == "map":
                result = self._map(input_data, config)
            elif operation == "flatten":
                result = self._flatten(input_data, config)
            elif operation == "group":
                result = self._group(input_data, config)
            elif operation == "convert":
                result = self._convert(input_data, config, output_format)
            else:
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"未知操作: {operation}"
                )
            
            # Format output
            if output_format == "csv" and isinstance(result, list):
                output = self._to_csv(result)
            else:
                output = result
            
            return SkillResult(
                success=True,
                output=output,
                metadata={
                    "operation": operation,
                    "input_count": len(input_data) if isinstance(input_data, (list, dict)) else 1,
                    "output_count": len(result) if isinstance(result, (list, dict)) else 1
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
    
    def _filter(self, data: List[Dict], config: Dict) -> List[Dict]:
        """Filter data based on conditions"""
        field = config.get("field")
        value = config.get("value")
        min_val = config.get("min")
        max_val = config.get("max")
        contains = config.get("contains")
        
        result = []
        for item in data:
            if not isinstance(item, dict):
                continue
            
            item_value = item.get(field)
            
            if value is not None and item_value == value:
                result.append(item)
            elif min_val is not None or max_val is not None:
                try:
                    val = float(item_value)
                    if (min_val is None or min_val <= val) and (max_val is None or val <= max_val):
                        result.append(item)
                except (TypeError, ValueError):
                    pass
            elif contains is not None and isinstance(item_value, str):
                if contains in item_value:
                    result.append(item)
            else:
                # Include non-None values by default
                if item_value is not None:
                    result.append(item)
        
        return result
    
    def _sort(self, data: List[Dict], config: Dict) -> List[Dict]:
        """Sort data by field"""
        field = config.get("field")
        reverse = config.get("reverse", False)
        
        if not field:
            return sorted(data, reverse=reverse)
        
        def sort_key(item):
            value = item.get(field) if isinstance(item, dict) else item
            # Try to convert to number for numeric sort
            try:
                return (0, float(value))
            except (TypeError, ValueError):
                return (1, str(value))
        
        return sorted(data, key=sort_key, reverse=reverse)
    
    def _map(self, data: List[Dict], config: Dict) -> List[Dict]:
        """Map/extract fields"""
        fields = config.get("fields", [])
        if not fields:
            return data
        
        result = []
        for item in data:
            if isinstance(item, dict):
                new_item = {f: item.get(f) for f in fields}
                result.append(new_item)
            else:
                result.append(item)
        
        return result
    
    def _flatten(self, data: Any, config: Dict) -> List:
        """Flatten nested structures"""
        separator = config.get("separator", ".")
        result = []
        
        def flatten_helper(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}{separator}{key}" if prefix else key
                    if isinstance(value, (dict, list)):
                        flatten_helper(value, new_key)
                    else:
                        result.append({new_key: value})
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_key = f"{prefix}[{i}]" if prefix else str(i)
                    flatten_helper(item, new_key)
        
        flatten_helper(data)
        return result
    
    def _group(self, data: List[Dict], config: Dict) -> Dict:
        """Group data by field"""
        field = config.get("field")
        if not field:
            return {"_ungrouped": data}
        
        groups = {}
        for item in data:
            if isinstance(item, dict):
                key = str(item.get(field, "_null"))
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)
        
        return groups
    
    def _convert(self, data: Any, config: Dict, output_format: str) -> Any:
        """Convert data format"""
        target_format = config.get("to", output_format)
        
        if target_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif target_format == "list":
            if isinstance(data, dict):
                return list(data.items())
            return list(data) if not isinstance(data, list) else data
        else:
            return data
    
    def _to_csv(self, data: List[Dict]) -> str:
        """Convert to CSV string"""
        if not data:
            return ""
        
        import io
        import csv
        
        output = io.StringIO()
        if data and isinstance(data[0], dict):
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(output)
            writer.writerows(data)
        
        return output.getvalue()
