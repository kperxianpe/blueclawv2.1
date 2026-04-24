#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw Skills Module

15 domain-specific skills with OpenClaw-style architecture.
Supports AI dynamic tool selection.
"""

# Base classes
from .base import Skill, SkillResult

# Registry and selector
from .registry import SkillRegistry
from .tool_selector import ToolSelector

# Import all skills to register them
# Filesystem
from .filesystem.read import FileReadSkill
from .filesystem.write import FileWriteSkill
from .filesystem.list import FileListSkill
from .filesystem.search import FileSearchSkill

# Code
from .code.analyze import CodeAnalyzeSkill
from .code.execute import CodeExecuteSkill

# Web
from .web.fetch import WebFetchSkill
from .web.search import WebSearchSkill

# Data
from .data.parse import DataParseSkill
from .data.transform import DataTransformSkill

# AI
from .ai.summarize import AISummarizeSkill
from .ai.translate import AITranslateSkill
from .ai.describe_image import AIDescribeImageSkill

# Document
from .document.read import DocReadSkill
from .document.write import DocWriteSkill

# System
from .system.shell import ShellExecuteSkill
from .system.info import SystemInfoSkill

__all__ = [
    # Base
    'Skill', 'SkillResult',
    # Registry & Selector
    'SkillRegistry', 'ToolSelector',
    # Skills
    'FileReadSkill', 'FileWriteSkill', 'FileListSkill', 'FileSearchSkill',
    'CodeAnalyzeSkill', 'CodeExecuteSkill',
    'WebFetchSkill', 'WebSearchSkill',
    'DataParseSkill', 'DataTransformSkill',
    'AISummarizeSkill', 'AITranslateSkill', 'AIDescribeImageSkill',
    'DocReadSkill', 'DocWriteSkill',
    'ShellExecuteSkill', 'SystemInfoSkill',
]
