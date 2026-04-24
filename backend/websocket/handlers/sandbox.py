#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sandbox 相关 WebSocket 处理器
Week 20.5 实现
"""
from backend.sandbox.docker_manager import sandbox_manager
from blueclaw.api.messages import Message


async def handle_sandbox_execute(websocket, payload: dict, server) -> dict:
    """
    sandbox.execute -> 在沙箱中执行代码
    """
    task_id = payload.get("task_id")
    code = payload.get("code")
    language = payload.get("language", "python")
    filename = payload.get("filename")  # 可选：执行文件而非代码片段
    
    if not code:
        return Message.create(
            "error",
            {"message": "Missing required parameter: code"},
            task_id=task_id
        ).to_dict()
    
    try:
        if filename:
            result = await sandbox_manager.execute_file(
                task_id=task_id,
                filename=filename,
                content=code,
                language=language
            )
        else:
            result = await sandbox_manager.execute_code(
                task_id=task_id,
                code=code,
                language=language
            )
        
        return Message.create(
            "sandbox.executed",
            {
                "success": result.success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error
            },
            task_id=task_id
        ).to_dict()
    except Exception as e:
        return Message.create(
            "error",
            {"message": f"Sandbox execution failed: {e}"},
            task_id=task_id
        ).to_dict()


async def handle_sandbox_create(websocket, payload: dict, server) -> dict:
    """
    sandbox.create -> 为任务创建沙箱
    """
    task_id = payload.get("task_id")
    
    if not task_id:
        return Message.create(
            "error",
            {"message": "Missing required parameter: task_id"},
            task_id=task_id
        ).to_dict()
    
    try:
        container_id = await sandbox_manager.create_sandbox(task_id)
        
        return Message.create(
            "sandbox.created",
            {
                "container_id": container_id[:12] if len(container_id) > 12 else container_id,
                "task_id": task_id
            },
            task_id=task_id
        ).to_dict()
    except Exception as e:
        return Message.create(
            "error",
            {"message": f"Failed to create sandbox: {e}"},
            task_id=task_id
        ).to_dict()


async def handle_sandbox_cleanup(websocket, payload: dict, server) -> dict:
    """
    sandbox.cleanup -> 清理任务沙箱
    """
    task_id = payload.get("task_id")
    
    if not task_id:
        return Message.create(
            "error",
            {"message": "Missing required parameter: task_id"},
            task_id=task_id
        ).to_dict()
    
    try:
        await sandbox_manager.cleanup(task_id)
        
        return Message.create(
            "sandbox.cleaned",
            {"task_id": task_id},
            task_id=task_id
        ).to_dict()
    except Exception as e:
        return Message.create(
            "error",
            {"message": f"Failed to cleanup sandbox: {e}"},
            task_id=task_id
        ).to_dict()
