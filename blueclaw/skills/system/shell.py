#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Shell Skill

Execute shell commands with strict safety restrictions.
"""

import subprocess
import shlex
from typing import Optional, List
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class ShellExecuteSkill(Skill):
    name = "shell_execute"
    description = "执行shell命令（高风险，需要确认）"
    category = "system"
    dangerous = True
    dangerous_level = 3  # Must be explicitly approved + sandbox
    
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的命令"
            },
            "timeout": {
                "type": "integer",
                "default": 30,
                "description": "超时时间（秒）",
                "minimum": 1,
                "maximum": 300
            },
            "working_dir": {
                "type": "string",
                "description": "工作目录"
            }
        },
        "required": ["command"]
    }
    
    capabilities = {
        "can_handle": ["系统命令", "文件操作命令", "信息查询命令"],
        "cannot_handle": ["删除系统文件", "网络扫描", "权限提升"],
        "typical_use_cases": [
            "查看系统信息",
            "列出目录内容",
            "运行脚本"
        ]
    }
    
    examples = [
        {
            "description": "列出目录",
            "input": {"command": "ls -la"},
            "output": "total 32\ndrwxr-xr-x..."
        }
    ]
    
    # Blocked dangerous commands
    BLOCKED_COMMANDS = [
        'rm -rf /', 'rm -rf /*', 'rm -rf ~', 'del /f /s /q',
        'format', 'mkfs', 'dd if=/dev/zero',
        ':(){ :|:& };:',  # Fork bomb
        'shutdown', 'reboot', 'halt', 'poweroff',
        'reg delete', 'rd /s /q',
    ]
    
    ALLOWED_COMMANDS = [
        'ls', 'dir', 'echo', 'cat', 'type', 'head', 'tail',
        'pwd', 'cd', 'whoami', 'date', 'time', 'uname', 'ver',
        'find', 'grep', 'sort', 'wc', 'diff', 'python', 'python3',
        'pip', 'pip3', 'node', 'npm', 'git', 'curl', 'wget',
    ]
    
    async def execute(self, command: str, timeout: int = 30,
                     working_dir: Optional[str] = None) -> SkillResult:
        import platform
        
        # Safety check: blocked commands
        cmd_lower = command.lower().strip()
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"命令被阻止: 包含危险操作 '{blocked}'",
                    suggestion="该命令可能造成系统损坏，不允许执行"
                )
        
        # Windows compatibility
        is_windows = platform.system() == "Windows"
        
        # Parse command
        try:
            cmd_parts = shlex.split(command)
            base_cmd = cmd_parts[0] if cmd_parts else ""
        except:
            base_cmd = command.split()[0] if command else ""
        
        # Windows: wrap with cmd /c for builtin commands
        if is_windows and base_cmd in ['echo', 'dir', 'type', 'ver', 'date', 'time']:
            cmd_parts = ['cmd', '/c'] + cmd_parts
        
        # Check if command is in allowed list (Windows compatible)
        allowed = any(base_cmd == a or base_cmd.endswith('/' + a) or 
                     base_cmd.endswith('\\' + a) for a in self.ALLOWED_COMMANDS)
        
        if not allowed:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"命令 '{base_cmd}' 不在允许列表中",
                suggestion=f"允许的命令: {', '.join(self.ALLOWED_COMMANDS[:10])}..."
            )
        
        try:
            # Execute command
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                shell=False  # Safer: don't use shell
            )
            
            output = result.stdout
            if result.stderr:
                output += "\n[stderr] " + result.stderr
            
            return SkillResult(
                success=result.returncode == 0,
                output=output,
                error_message=f"Exit code: {result.returncode}" if result.returncode != 0 else None,
                metadata={
                    "command": command,
                    "returncode": result.returncode,
                    "stdout_length": len(result.stdout),
                    "stderr_length": len(result.stderr)
                }
            )
            
        except subprocess.TimeoutExpired:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"命令执行超时（{timeout}秒）",
                suggestion="增加 timeout 参数，或优化命令"
            )
        except FileNotFoundError:
            return SkillResult(
                success=False,
                output=None,
                error_message=f"命令未找到: {base_cmd}",
                suggestion="检查命令是否正确安装"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error_message=str(e)
            )
