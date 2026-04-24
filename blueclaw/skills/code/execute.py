#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Execute Skill

Execute code in sandboxed environment with safety checks.
"""

import asyncio
import sys
from io import StringIO
from typing import Optional, Dict
from contextlib import redirect_stdout, redirect_stderr
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class CodeExecuteSkill(Skill):
    name = "code_execute"
    description = "执行Python代码片段（受限环境）"
    category = "code"
    dangerous = True
    dangerous_level = 2  # Requires confirmation + timeout
    
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "要执行的Python代码"
            },
            "timeout": {
                "type": "integer",
                "description": "执行超时时间（秒）",
                "default": 5,
                "minimum": 1,
                "maximum": 30
            },
            "allow_imports": {
                "type": "boolean",
                "default": False,
                "description": "是否允许import语句"
            }
        },
        "required": ["code"]
    }
    
    capabilities = {
        "can_handle": ["Python表达式", "简单计算", "数据处理"],
        "cannot_handle": ["网络请求", "文件操作", "系统命令", "长时间运行"],
        "typical_use_cases": [
            "执行数学计算",
            "测试代码片段",
            "数据转换",
            "格式验证"
        ]
    }
    
    examples = [
        {
            "description": "简单计算",
            "input": {"code": "2 + 2 * 10"},
            "output": "22"
        },
        {
            "description": "处理列表",
            "input": {"code": "[x**2 for x in range(5)]"},
            "output": "[0, 1, 4, 9, 16]"
        }
    ]
    
    async def execute(self, code: str, timeout: int = 5, 
                     allow_imports: bool = False) -> SkillResult:
        # Safety checks
        dangerous_keywords = [
            'eval', 'exec', 'compile', '__import__', 'open', 
            'subprocess', 'os.system', 'os.popen', 'input'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in code:
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"代码包含危险操作: {keyword}",
                    suggestion="避免使用 eval, exec, open, subprocess 等危险函数"
                )
        
        # Check imports
        if not allow_imports:
            if 'import ' in code or 'from ' in code:
                return SkillResult(
                    success=False,
                    output=None,
                    error_message="代码包含import语句",
                    suggestion="设置 allow_imports=True 允许导入模块"
                )
        
        # Execute in isolated environment
        return await self._execute_sandboxed(code, timeout)
    
    async def _execute_sandboxed(self, code: str, timeout: int) -> SkillResult:
        """Execute code in sandboxed environment"""
        
        def run_code():
            # Create restricted globals
            safe_globals = {
                '__builtins__': {
                    'len': len,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'pow': pow,
                    'divmod': divmod,
                    'chr': chr,
                    'ord': ord,
                    'bin': bin,
                    'hex': hex,
                    'oct': oct,
                    'sorted': sorted,
                    'reversed': reversed,
                    'list': list,
                    'dict': dict,
                    'set': set,
                    'tuple': tuple,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'type': type,
                    'isinstance': isinstance,
                    'hasattr': hasattr,
                    'getattr': getattr,
                    'print': print,
                    'Exception': Exception,
                    'ValueError': ValueError,
                    'TypeError': TypeError,
                    'KeyError': KeyError,
                    'IndexError': IndexError,
                }
            }
            
            stdout_buffer = StringIO()
            stderr_buffer = StringIO()
            
            try:
                with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                    # Execute code
                    exec(code, safe_globals)
                
                output = stdout_buffer.getvalue()
                error = stderr_buffer.getvalue()
                
                # Get the last expression value if any
                last_value = None
                try:
                    last_value = eval(compile(code, '<string>', 'eval'), safe_globals)
                except:
                    pass
                
                return {
                    "success": error == "",
                    "output": output if output else str(last_value) if last_value is not None else None,
                    "error": error if error else None,
                    "last_value": last_value
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "output": stdout_buffer.getvalue(),
                    "error": f"{type(e).__name__}: {e}",
                    "last_value": None
                }
        
        try:
            # Run with timeout using asyncio
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, run_code),
                timeout=timeout
            )
            
            return SkillResult(
                success=result["success"],
                output=result["output"],
                error_message=result["error"],
                metadata={"timeout_used": timeout}
            )
            
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"执行超时（{timeout}秒）",
                suggestion="优化代码或增加 timeout 参数"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
