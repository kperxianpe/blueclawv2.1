#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具图标相关 WebSocket 处理器
Week 20.5 实现
"""
from backend.tools.registry import tool_registry
from blueclaw.api.messages import Message


async def handle_tools_list(websocket, payload: dict, server) -> dict:
    """
    tools.list -> 获取可用工具图标列表
    """
    try:
        # 刷新工具列表
        count = await tool_registry.refresh()
        tools = tool_registry.list_all()
        
        return Message.create(
            "tools.listed",
            {
                "tools": [t.to_dict() for t in tools],
                "count": len(tools)
            },
            task_id=payload.get("task_id")
        ).to_dict()
    except Exception as e:
        return Message.create(
            "error",
            {"message": f"Failed to list tools: {e}"},
            task_id=payload.get("task_id")
        ).to_dict()


async def handle_tools_inspect(websocket, payload: dict, server) -> dict:
    """
    tools.inspect -> 查看工具详情
    """
    tool_id = payload.get("tool_id")
    
    if not tool_id:
        return Message.create(
            "error",
            {"message": "Missing tool_id"},
            task_id=payload.get("task_id")
        ).to_dict()
    
    tool = tool_registry.get(tool_id)
    if not tool:
        return Message.create(
            "error",
            {"message": f"Tool not found: {tool_id}"},
            task_id=payload.get("task_id")
        ).to_dict()
    
    return Message.create(
        "tools.inspected",
        {
            "id": tool.id,
            "type": tool.type.value,
            "name": tool.name,
            "icon": tool.icon,
            "color": tool.color,
            "description": tool.description,
            "config": tool.config,
            "source": tool.source
        },
        task_id=payload.get("task_id")
    ).to_dict()
