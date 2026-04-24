# -*- coding: utf-8 -*-
"""Shell Skill - Terminal command execution"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Optional

from .base_skill import BaseSkill, SkillResult, SkillParameter, PermissionLevel


class ShellSkill(BaseSkill):
    """Shell command execution skill"""
    
    name = "shell"
    description = "Execute shell commands (bash/cmd/PowerShell)"
    version = "1.0.0"
    permission_level = PermissionLevel.SYSTEM
    requires_confirmation = True
    timeout = 30.0
    
    parameters = [
        SkillParameter("command", "string", "Shell command to execute", required=True),
        SkillParameter("working_dir", "string", "Working directory", required=False),
        SkillParameter("timeout", "number", "Timeout in seconds", required=False, default=30),
    ]
    
    DANGEROUS_PATTERNS = [
        r'\brm\s+-rf\s+/',
        r'\bformat\s+',
        r'\bdd\s+if=.*of=/dev/',
        r'\bdel\s+/[fqs]',
        r'\brd\s+/s',
    ]
    
    async def execute(self, **kwargs) -> SkillResult:
        command = kwargs.get('command')
        if not command:
            return SkillResult.fail(error="Missing required parameter: command")
        
        if self._is_dangerous(command):
            return SkillResult.fail(
                error=f"Command blocked for safety: {command}"
            )
        
        working_dir = kwargs.get('working_dir')
        timeout = kwargs.get('timeout', self.timeout)
        
        try:
            env_vars = os.environ.copy()
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env_vars
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return SkillResult.fail(error=f"Command timed out after {timeout}s")
            
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            success = process.returncode == 0
            
            return SkillResult(
                success=success,
                data={
                    'stdout': stdout_str,
                    'stderr': stderr_str,
                    'returncode': process.returncode
                },
                error=stderr_str if not success else "",
                metadata={'command': command, 'returncode': process.returncode}
            )
            
        except Exception as e:
            return SkillResult.fail(error=f"Shell execution failed: {str(e)}")
    
    def _is_dangerous(self, command: str) -> bool:
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False
