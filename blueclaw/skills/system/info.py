#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Info Skill

Get system information safely.
"""

import platform
import sys
import os
from typing import Optional, Dict
from pathlib import Path
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class SystemInfoSkill(Skill):
    name = "system_info"
    description = "获取系统和环境信息"
    category = "system"
    
    parameters = {
        "type": "object",
        "properties": {
            "info_type": {
                "type": "string",
                "enum": ["all", "platform", "python", "env", "cwd", "user"],
                "default": "all",
                "description": "信息类型"
            }
        },
        "required": []
    }
    
    capabilities = {
        "can_handle": ["系统平台信息", "Python环境", "环境变量", "当前目录"],
        "cannot_handle": ["敏感系统信息", "其他用户数据"],
        "typical_use_cases": [
            "检查系统环境",
            "调试兼容性问题",
            "查看Python版本"
        ]
    }
    
    examples = [
        {
            "description": "获取所有信息",
            "input": {},
            "output": "{platform: ..., python: ...}"
        },
        {
            "description": "获取Python信息",
            "input": {"info_type": "python"},
            "output": "{version: '3.12.0', ...}"
        }
    ]
    
    async def execute(self, info_type: str = "all") -> SkillResult:
        try:
            result = {}
            
            if info_type in ["all", "platform"]:
                result["platform"] = {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "node": platform.node()
                }
            
            if info_type in ["all", "python"]:
                result["python"] = {
                    "version": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "executable": sys.executable,
                    "path": sys.path[:3]  # Limit path output
                }
            
            if info_type in ["all", "env"]:
                # Safe environment variables only
                safe_vars = ['PATH', 'HOME', 'USER', 'USERNAME', 'SHELL', 
                           'LANG', 'TERM', 'EDITOR', 'PWD']
                result["env"] = {k: os.environ.get(k) for k in safe_vars 
                               if k in os.environ}
            
            if info_type in ["all", "cwd"]:
                result["cwd"] = str(Path.cwd())
            
            if info_type in ["all", "user"]:
                result["user"] = {
                    "name": os.environ.get('USERNAME') or os.environ.get('USER'),
                    "home": str(Path.home())
                }
            
            return SkillResult(
                success=True,
                output=result,
                metadata={"info_type": info_type}
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
