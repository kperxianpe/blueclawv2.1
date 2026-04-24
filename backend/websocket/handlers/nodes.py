#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节点相关 WebSocket 处理器（工具绑定/解锁）
Week 20.5 实现
"""
from backend.core.task_manager import task_manager
from backend.tools.models import ToolBinding
from blueclaw.api.messages import Message


async def handle_node_bind_tool(websocket, payload: dict, server) -> dict:
    """
    node.bind_tool -> 绑定工具图标到节点
    """
    task_id = payload.get("task_id")
    step_id = payload.get("step_id")
    tool_id = payload.get("tool_id")
    locked = payload.get("locked", True)  # 默认锁定
    
    if not all([task_id, step_id, tool_id]):
        return Message.create(
            "error",
            {"message": "Missing required parameters: task_id, step_id, tool_id"},
            task_id=task_id
        ).to_dict()
    
    task = task_manager.get_task(task_id)
    if not task or not task.execution_blueprint:
        return Message.create(
            "error",
            {"message": "Task or blueprint not found"},
            task_id=task_id
        ).to_dict()
    
    # 查找步骤
    step = None
    for s in task.execution_blueprint.steps:
        if s.id == step_id:
            step = s
            break
    
    if not step:
        return Message.create(
            "error",
            {"message": f"Step not found: {step_id}"},
            task_id=task_id
        ).to_dict()
    
    # 验证工具存在
    from backend.tools.registry import tool_registry
    tool = tool_registry.get(tool_id)
    if not tool:
        return Message.create(
            "error",
            {"message": f"Tool not found: {tool_id}"},
            task_id=task_id
        ).to_dict()
    
    # 绑定工具
    step.tool_binding = ToolBinding(
        tool_icon_id=tool_id,
        locked=locked
    )
    
    # 推送节点更新
    await server.broadcast_to_task(
        task_id,
        Message.create(
            "node.tool_bound",
            {
                "step_id": step_id,
                "tool_id": tool_id,
                "locked": locked,
                "tool_preview": {
                    "icon": tool.icon,
                    "color": tool.color,
                    "name": tool.name
                }
            },
            task_id=task_id
        ).to_dict()
    )
    
    return Message.create(
        "node.bind_tool_success",
        {
            "step_id": step_id,
            "tool_id": tool_id,
            "locked": locked
        },
        task_id=task_id
    ).to_dict()


async def handle_node_unlock_tool(websocket, payload: dict, server) -> dict:
    """
    node.unlock_tool -> 解锁节点工具（恢复自动选择）
    """
    task_id = payload.get("task_id")
    step_id = payload.get("step_id")
    
    if not all([task_id, step_id]):
        return Message.create(
            "error",
            {"message": "Missing required parameters: task_id, step_id"},
            task_id=task_id
        ).to_dict()
    
    task = task_manager.get_task(task_id)
    if not task or not task.execution_blueprint:
        return Message.create(
            "error",
            {"message": "Task or blueprint not found"},
            task_id=task_id
        ).to_dict()
    
    step = None
    for s in task.execution_blueprint.steps:
        if s.id == step_id:
            step = s
            break
    
    if not step:
        return Message.create(
            "error",
            {"message": f"Step not found: {step_id}"},
            task_id=task_id
        ).to_dict()
    
    # 解锁工具
    if step.tool_binding:
        step.tool_binding.locked = False
        tool_id = step.tool_binding.tool_icon_id
    else:
        tool_id = None
    
    # 推送更新
    await server.broadcast_to_task(
        task_id,
        Message.create(
            "node.tool_unlocked",
            {
                "step_id": step_id,
                "tool_id": tool_id
            },
            task_id=task_id
        ).to_dict()
    )
    
    return Message.create(
        "node.unlock_tool_success",
        {
            "step_id": step_id,
            "tool_id": tool_id
        },
        task_id=task_id
    ).to_dict()
