# -*- coding: utf-8 -*-
"""Code Skill - Execute Python code"""

from __future__ import annotations

import ast
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict

from .base_skill import BaseSkill, SkillResult, SkillParameter, PermissionLevel


class CodeSkill(BaseSkill):
    """Code execution skill"""
    
    name = "code"
    description = "Execute Python code for data processing"
    version = "1.0.0"
    permission_level = PermissionLevel.WRITE
    timeout = 60.0
    
    parameters = [
        SkillParameter("code", "string", "Python code to execute", required=True),
        SkillParameter("variables", "object", "Input variables", required=False),
    ]
    
    ALLOWED_MODULES = {
        'math', 'random', 'datetime', 'json', 're', 'string',
        'collections', 'itertools', 'statistics', 'typing', 'pathlib'
    }
    
    DANGEROUS_PATTERNS = ['__import__', 'eval(', 'exec(', 'compile(', 'importlib']
    
    async def execute(self, **kwargs) -> SkillResult:
        code = kwargs.get('code')
        if not code:
            return SkillResult.fail(error="Missing required parameter: code")
        
        variables = kwargs.get('variables', {})
        
        if not self._is_safe(code):
            return SkillResult.fail(error="Code contains unsafe operations")
        
        try:
            safe_globals = {
                '__builtins__': {
                    'True': True, 'False': False, 'None': None,
                    'abs': abs, 'all': all, 'any': any, 'bin': bin,
                    'bool': bool, 'bytes': bytes, 'chr': chr, 'complex': complex,
                    'dict': dict, 'dir': dir, 'divmod': divmod, 'enumerate': enumerate,
                    'filter': filter, 'float': float, 'format': format,
                    'hasattr': hasattr, 'hash': hash, 'hex': hex, 'id': id, 'int': int,
                    'isinstance': isinstance, 'issubclass': issubclass,
                    'iter': iter, 'len': len, 'list': list, 'map': map,
                    'max': max, 'min': min, 'next': next, 'oct': oct,
                    'ord': ord, 'pow': pow, 'print': print, 'range': range,
                    'repr': repr, 'reversed': reversed, 'round': round,
                    'set': set, 'slice': slice, 'sorted': sorted,
                    'str': str, 'sum': sum, 'tuple': tuple, 'type': type,
                    'vars': vars, 'zip': zip
                }
            }
            
            for module_name in self.ALLOWED_MODULES:
                try:
                    module = __import__(module_name)
                    safe_globals[module_name] = module
                except ImportError:
                    pass
            
            safe_globals.update(variables)
            
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            
            local_vars = {}
            
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(code, safe_globals, local_vars)
            
            return SkillResult(
                success=True,
                data={
                    'result': local_vars.get('result', stdout_buffer.getvalue()),
                    'stdout': stdout_buffer.getvalue(),
                    'stderr': stderr_buffer.getvalue(),
                    'variables': {k: v for k, v in local_vars.items() if not k.startswith('_')}
                },
                metadata={'code_lines': len(code.split('\n'))}
            )
            
        except Exception as e:
            return SkillResult.fail(error=f"{str(e)}\n{traceback.format_exc()}")
    
    def _is_safe(self, code: str) -> bool:
        code_lower = code.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in code_lower:
                return False
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] not in self.ALLOWED_MODULES:
                            return False
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.module.split('.')[0] not in self.ALLOWED_MODULES:
                            return False
            return True
        except:
            return False
