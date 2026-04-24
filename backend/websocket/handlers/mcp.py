#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 相关 WebSocket 处理器
Week 20.5 实现
"""
from backend.mcp.client import mcp_registry
from backend.tools.registry import tool_registry
from blueclaw.api.messages import Message


async def handle_mcp_execute(websocket, payload: dict, server) -> dict:
    """
    mcp.execute -> 直接执行 MCP Tool
    """
    task_id = payload.get("task_id")
    server_name = payload.get("server_name")
    tool_name = payload.get("tool_name")
    parameters = payload.get("parameters", {})
    
    if not all([server_name, tool_name]):
        return Message.create(
            "error",
            {"message": "Missing required parameters: server_name, tool_name"},
            task_id=task_id
        ).to_dict()
    
    try:
        result = await mcp_registry.call_tool(
            server_name=server_name,
            tool_name=tool_name,
            parameters=parameters
        )
        
        return Message.create(
            "mcp.executed",
            {
                "success": result.success,
                "result": result.data,
                "error": result.error
            },
            task_id=task_id
        ).to_dict()
    except Exception as e:
        return Message.create(
            "error",
            {"message": f"MCP execution failed: {e}"},
            task_id=task_id
        ).to_dict()


async def handle_mcp_refresh(websocket, payload: dict, server) -> dict:
    """
    mcp.refresh -> 刷新 MCP 工具列表
    """
    task_id = payload.get("task_id")
    
    try:
        count = await tool_registry.refresh()
        
        return Message.create(
            "mcp.refreshed",
            {
                "tools_count": count,
                "mcp_tools": [
                    t.to_dict() for t in tool_registry.filter_by_type(
                        tool_registry._icons[list(tool_registry._icons.keys())[0]].type
                        if tool_registry._icons else None
                    )
                ] if hasattr(tool_registry, '_icons') else []
            },
            task_id=task_id
        ).to_dict()
    except Exception as e:
        return Message.create(
            "error",
            {"message": f"Failed to refresh MCP tools: {e}"},
            task_id=task_id
        ).to_dict()
