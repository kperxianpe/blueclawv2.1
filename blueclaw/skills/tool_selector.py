#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Tool Selector Module

Selects best skill combinations based on task descriptions.
"""

from typing import List, Dict, Optional
import json
from .registry import SkillRegistry


class ToolSelector:
    """
    AI Tool Selector
    
    Recommends skill combinations based on task descriptions.
    """
    
    def __init__(self):
        self.registry = SkillRegistry()
        
        # Task keyword to skill mappings
        self._task_mappings = {
            # Filesystem
            "file_read": ["读取", "read", "查看", "view", "打开", "open", "内容", "content"],
            "file_write": ["写入", "write", "保存", "save", "创建", "create", "修改", "edit"],
            "file_list": ["目录", "folder", "list", "列举", "dir", "ls", "文件列表"],
            "file_search": ["搜索", "search", "查找", "find", "glob", "模式", "pattern"],
            
            # Code
            "code_execute": ["执行", "execute", "运行", "run", "python", "代码运行"],
            "code_analyze": ["分析代码", "code analyze", "代码分析", "review", "检查", "lint"],
            
            # Web
            "web_fetch": ["获取", "fetch", "下载", "download", "网页内容", "page content"],
            "web_search": ["搜索", "search", "查找资料", "查询", "google", "bing", "百度"],
            
            # Data
            "data_parse": ["解析", "parse", "json", "csv", "xml", "数据读取", "data read"],
            "data_transform": ["转换", "transform", "格式化", "format", "清洗", "clean"],
            
            # AI
            "ai_summarize": ["总结", "summarize", "摘要", "summary", "概述", "提炼"],
            "ai_translate": ["翻译", "translate", "中英", "英中", "中文", "英文"],
            "ai_describe_image": ["图片", "image", "图像", "识别", "describe", "描述图片"],
            
            # Document
            "doc_read": ["读取文档", "read doc", "word", "pdf", "excel", "文档读取"],
            "doc_write": ["写入文档", "write doc", "生成文档", "导出", "export"],
            
            # System
            "shell_execute": ["shell", "命令", "command", "bash", "终端", "terminal"],
            "system_info": ["系统", "system", "信息", "info", "环境", "environment"],
        }
    
    def get_tools_for_task(self, task_description: str) -> List[str]:
        """
        Get recommended tools for a task
        
        Args:
            task_description: Task description
            
        Returns:
            List of recommended tool names
        """
        task_lower = task_description.lower()
        tools = []
        scores = {}
        
        # Score each skill based on keyword matches
        for tool_name, keywords in self._task_mappings.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in task_lower:
                    score += 1
            if score > 0:
                scores[tool_name] = score
        
        # Sort by score descending
        sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        tools = [tool for tool, _ in sorted_tools]
        
        # Add related tools based on combinations
        tools = self._add_related_tools(tools, task_lower)
        
        return tools
    
    def _add_related_tools(self, tools: List[str], task_lower: str) -> List[str]:
        """Add related tools based on common patterns"""
        result = list(tools)
        
        # If reading files, also need to list them
        if "file_read" in tools and "file_list" not in result:
            if any(k in task_lower for k in ["目录", "folder", "dir", "ls"]):
                result.insert(1, "file_list")
        
        # If searching, also need to fetch
        if "web_search" in tools and "web_fetch" not in result:
            if any(k in task_lower for k in ["获取", "fetch", "下载", "download"]):
                result.append("web_fetch")
        
        # If analyzing code, also need to read it
        if "code_analyze" in tools and "file_read" not in result:
            result.insert(0, "file_read")
        
        return result
    
    def generate_tools_prompt(self, tool_names: List[str] = None) -> str:
        """
        Generate tools description prompt for LLM
        
        Args:
            tool_names: List of tool names, None for all
            
        Returns:
            Formatted prompt string
        """
        if tool_names is None:
            skills = self.registry.list_by_category()
        else:
            skills = {name: self.registry.get(name) for name in tool_names}
        
        prompt_parts = ["Available tools:\n"]
        
        for name, skill in skills.items():
            if not skill:
                continue
            
            risk_mark = ""
            if skill.dangerous_level == 1:
                risk_mark = " ⚠️"
            elif skill.dangerous_level == 2:
                risk_mark = " ⚠️⚠️"
            elif skill.dangerous_level == 3:
                risk_mark = " ⚠️⚠️⚠️"
            
            prompt_parts.append(f"\n## {name}{risk_mark}")
            prompt_parts.append(f"Description: {skill.description}")
            prompt_parts.append(f"Parameters: {json.dumps(skill.parameters, indent=2, ensure_ascii=False)}")
            
            if skill.examples:
                prompt_parts.append("Examples:")
                for ex in skill.examples[:2]:
                    prompt_parts.append(f"  - {ex.get('description', 'Example')}")
                    prompt_parts.append(f"    Input: {json.dumps(ex.get('input', {}), ensure_ascii=False)}")
        
        prompt_parts.append("\nUse the tools above to complete the task.")
        return "\n".join(prompt_parts)
    
    def check_dangerous_operations(self, tool_names: List[str]) -> List[Dict]:
        """
        Check for dangerous operations
        
        Args:
            tool_names: List of tool names
            
        Returns:
            List of dangerous operation details
        """
        dangerous = []
        for name in tool_names:
            skill = self.registry.get(name)
            if skill and skill.dangerous:
                dangerous.append({
                    "tool": name,
                    "level": skill.dangerous_level,
                    "description": skill.description
                })
        return dangerous
    
    def validate_tool_chain(self, tool_names: List[str]) -> tuple:
        """
        Validate a chain of tools
        
        Returns:
            (is_valid, error_message)
        """
        for name in tool_names:
            if not self.registry.get(name):
                return False, f"Unknown tool: {name}"
        
        # Check for dangerous combinations
        dangerous = self.check_dangerous_operations(tool_names)
        if dangerous:
            max_level = max(d["level"] for d in dangerous)
            if max_level >= 2:
                return False, f"Contains high-risk operations: {[d['tool'] for d in dangerous]}"
        
        return True, ""
    
    def suggest_alternatives(self, failed_tool: str, error: str) -> List[str]:
        """
        Suggest alternative tools when one fails
        
        Args:
            failed_tool: Name of failed tool
            error: Error message
            
        Returns:
            List of alternative tool names
        """
        error_lower = error.lower()
        suggestions = []
        
        if failed_tool == "file_read":
            if "encoding" in error_lower:
                suggestions.append("file_read with encoding='latin-1'")
            if "not found" in error_lower:
                suggestions.append("file_list to verify path")
        
        elif failed_tool == "web_fetch":
            if "timeout" in error_lower or "connection" in error_lower:
                suggestions.append("Retry with timeout parameter")
        
        return suggestions
