#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToolSelector - 智能工具选择器
Week 20.5 实现：根据任务描述和 hint 选择最合适的工具
"""
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ToolSelection:
    """工具选择结果"""
    tool_id: str
    name: str
    type: str
    confidence: float


class ToolSelector:
    """智能工具选择器"""
    
    async def select(
        self,
        direction: str,
        hint: Optional[str],
        available_tools: List['ToolIcon']
    ) -> ToolSelection:
        """
        选择最合适的工具
        
        策略：
        1. hint 精确匹配（置信度 0.95）
        2. 关键词匹配（置信度 0.7-0.9）
        3. 默认选择第一个可用工具（置信度 0.5）
        """
        from backend.tools.registry import ToolType
        
        # 1. hint 精确匹配
        if hint:
            for tool in available_tools:
                config_hint = tool.config.get("tool_hint", "")
                if config_hint and hint.lower() in config_hint.lower():
                    return ToolSelection(
                        tool_id=tool.id,
                        name=tool.name,
                        type=tool.type.value,
                        confidence=0.95
                    )
        
        # 2. 关键词匹配
        keywords = self._extract_keywords(direction)
        
        best_match = None
        best_score = 0.0
        
        for tool in available_tools:
            score = self._calculate_match_score(keywords, tool)
            if score > best_score:
                best_score = score
                best_match = tool
        
        if best_match and best_score > 0.6:
            return ToolSelection(
                tool_id=best_match.id,
                name=best_match.name,
                type=best_match.type.value,
                confidence=min(0.9, best_score)
            )
        
        # 3. 默认选择（优先 MCP，其次 Skill，最后 Adapter）
        mcp_tools = [t for t in available_tools if t.type == ToolType.MCP]
        if mcp_tools:
            return ToolSelection(
                tool_id=mcp_tools[0].id,
                name=mcp_tools[0].name,
                type="mcp",
                confidence=0.5
            )
        
        skills = [t for t in available_tools if t.type == ToolType.SKILL]
        if skills:
            return ToolSelection(
                tool_id=skills[0].id,
                name=skills[0].name,
                type="skill",
                confidence=0.5
            )
        
        adapters = [t for t in available_tools if t.type == ToolType.ADAPTER]
        if adapters:
            return ToolSelection(
                tool_id=adapters[0].id,
                name=adapters[0].name,
                type="adapter",
                confidence=0.5
            )
        
        raise ValueError("No available tools")
    
    def _extract_keywords(self, direction: str) -> List[str]:
        """提取关键词"""
        # 简单实现：分词并过滤停用词
        words = direction.lower().split()
        stopwords = {
            "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
            "和", "在", "查询", "获取", "执行", "使用", "进行", "完成"
        }
        return [w for w in words if w not in stopwords and len(w) > 1]
    
    def _calculate_match_score(self, keywords: List[str], tool: 'ToolIcon') -> float:
        """计算匹配分数"""
        text = f"{tool.name} {tool.description}".lower()
        
        matches = sum(1 for kw in keywords if kw in text)
        if not keywords:
            return 0.0
        
        base_score = matches / len(keywords)
        
        # 根据工具类型加权
        from backend.tools.registry import ToolType
        type_weights = {
            ToolType.MCP: 1.1,
            ToolType.SKILL: 1.0,
            ToolType.ADAPTER: 0.9
        }
        weight = type_weights.get(tool.type, 1.0)
        
        return min(0.95, base_score * weight + matches * 0.05)


# 用于类型提示
from backend.tools.registry import ToolIcon
