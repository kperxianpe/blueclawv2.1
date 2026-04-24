#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter 相关 WebSocket 处理器
用户通过拖拽、绑定、执行 Adapter
"""
import asyncio
import uuid

from backend.adapter.models import (
    adapter_registry, Adapter, AdapterType, AdapterLevel, 
    MultimodalInput, BlueprintConfig, BlueprintStep, AdapterAttachment
)
from backend.adapter.execution_engine import adapter_execution_engine
from blueclaw.api.messages import Message


def _serialize_adapter(adapter: Adapter) -> dict:
    """序列化 Adapter 为前端可用格式"""
    return {
        "id": adapter.id,
        "name": adapter.name,
        "description": adapter.description,
        "icon": adapter.icon,
        "color": adapter.color,
        "type": adapter.adapter_type.value,
        "level": adapter.level.value,
        "inputs": [
            {
                "type": inp.type,
                "mime_type": inp.mime_type,
                "has_thumbnail": inp.thumbnail is not None,
                "is_tool": inp.type in ["tool", "skill"],
                "is_adapter": inp.type == "adapter"
            }
            for inp in adapter.inputs
        ],
        "input_count": len(adapter.inputs),
        "has_children": len(adapter.children) > 0,
        "children_count": len(adapter.children),
        "is_template": adapter.is_template,
        "created_by": adapter.created_by,
        "blueprint": adapter.blueprint_config.to_dict() if adapter.blueprint_config else None
    }


async def handle_adapter_list(websocket, payload: dict, server) -> dict:
    """adapter.list → 获取 Adapter 列表（显示在左侧面板）"""
    filter_type = payload.get("filter_type")  # single/blueprint/agent
    
    adapters = adapter_registry.list_all(
        AdapterType(filter_type) if filter_type else None
    )
    
    return Message.create(
        "adapter.listed",
        {
            "adapters": [_serialize_adapter(a) for a in adapters],
            "count": len(adapters)
        },
        task_id=payload.get("task_id")
    )


async def handle_adapter_get(websocket, payload: dict, server) -> dict:
    """adapter.get → 获取 Adapter 详情（用于编辑/预览）"""
    adapter_id = payload.get("adapter_id")
    
    adapter = adapter_registry.get(adapter_id)
    if not adapter:
        return Message.create(
            "error",
            {"message": f"Adapter not found: {adapter_id}"},
            task_id=payload.get("task_id")
        )
    
    return Message.create(
        "adapter.detail",
        _serialize_adapter(adapter),
        task_id=payload.get("task_id")
    )


async def handle_adapter_create(websocket, payload: dict, server) -> dict:
    """adapter.create → 创建新 Adapter"""
    adapter = Adapter(
        id=f"adapter_{uuid.uuid4().hex[:12]}",
        name=payload.get("name", "Untitled Adapter"),
        description=payload.get("description", ""),
        icon=payload.get("icon", "📦"),
        color=payload.get("color", "#FCD34D"),
        adapter_type=AdapterType(payload.get("type", "single")),
        is_template=payload.get("is_template", False)
    )
    
    created = adapter_registry.create(adapter)
    
    return Message.create(
        "adapter.created",
        _serialize_adapter(created),
        task_id=payload.get("task_id")
    )


async def handle_adapter_update(websocket, payload: dict, server) -> dict:
    """adapter.update → 更新 Adapter"""
    adapter_id = payload.get("adapter_id")
    updates = payload.get("updates", {})
    
    updated = adapter_registry.update(adapter_id, updates)
    
    if not updated:
        return Message.create(
            "error",
            {"message": f"Adapter not found: {adapter_id}"},
            task_id=payload.get("task_id")
        )
    
    return Message.create(
        "adapter.updated",
        _serialize_adapter(updated),
        task_id=payload.get("task_id")
    )


async def handle_adapter_add_input(websocket, payload: dict, server) -> dict:
    """adapter.add_input → 添加多模态输入"""
    adapter_id = payload.get("adapter_id")
    input_data = payload.get("input", {})
    
    adapter = adapter_registry.get(adapter_id)
    if not adapter:
        return Message.create(
            "error",
            {"message": f"Adapter not found: {adapter_id}"},
            task_id=payload.get("task_id")
        )
    
    new_input = MultimodalInput(
        type=input_data.get("type"),
        source=input_data.get("source"),
        mime_type=input_data.get("mime_type"),
        metadata=input_data.get("metadata", {}),
        thumbnail=input_data.get("thumbnail"),
        ref_id=input_data.get("ref_id"),
        ref_type=input_data.get("ref_type")
    )
    
    adapter.inputs.append(new_input)
    updated = adapter_registry.update(adapter_id, {"inputs": adapter.inputs})
    
    return Message.create(
        "adapter.input_added",
        {"adapter_id": adapter_id, "input_index": len(adapter.inputs) - 1},
        task_id=payload.get("task_id")
    )


async def handle_adapter_attach_to_step(websocket, payload: dict, server) -> dict:
    """
    adapter.attach_to_step → 绑定 Adapter 到蓝图步骤
    用户拖拽黄色方块到节点上的操作
    """
    task_id = payload.get("task_id")
    step_id = payload.get("step_id")
    adapter_id = payload.get("adapter_id")
    locked = payload.get("locked", True)
    
    # 获取 Adapter 快照（深拷贝，防止原 Adapter 修改影响已绑定任务）
    adapter = adapter_registry.get_snapshot(adapter_id)
    if not adapter:
        return Message.create(
            "error",
            {"message": f"Adapter not found: {adapter_id}"},
            task_id=task_id
        )
    
    # 更新步骤
    try:
        from backend.core.task_manager import task_manager
        from blueclaw.core.execution_engine import ExecutionStep
        
        task = task_manager.get_task(task_id)
        if not task or not task.execution_blueprint:
            return Message.create(
                "error",
                {"message": "Task or blueprint not found"},
                task_id=task_id
            )
        
        # 查找步骤并绑定
        step_found = False
        for step in task.execution_blueprint.steps:
            if step.id == step_id:
                # 初始化 attached_adapters 属性（如果不存在）
                if not hasattr(step, "attached_adapters"):
                    step.attached_adapters = []
                
                attachment = AdapterAttachment(
                    adapter_id=adapter_id,
                    adapter_ref=adapter,
                    position="top-right",
                    locked=locked,
                    execution_order=len(step.attached_adapters)
                )
                step.attached_adapters.append(attachment)
                step_found = True
                break
        
        if not step_found:
            return Message.create(
                "error",
                {"message": f"Step not found: {step_id}"},
                task_id=task_id
            )
        
        # 广播更新到前端（实时显示在节点右上角）
        await server.broadcast_to_task(
            task_id,
            Message.create(
                "adapter.attached",
                {
                    "step_id": step_id,
                    "adapter_id": adapter_id,
                    "adapter_preview": {
                        "icon": adapter.icon,
                        "color": adapter.color,
                        "name": adapter.name,
                        "locked": locked
                    },
                    "total_attached": len(step.attached_adapters)
                },
                task_id=task_id
            )
        )
        
        return Message.create(
            "adapter.attach_success",
            {"step_id": step_id, "adapter_id": adapter_id},
            task_id=task_id
        )
        
    except ImportError:
        # Mock 模式
        return Message.create(
            "adapter.attach_success",
            {"step_id": step_id, "adapter_id": adapter_id, "mock": True},
            task_id=task_id
        )


async def handle_adapter_enter_edit(websocket, payload: dict, server) -> dict:
    """
    adapter.enter_edit → 进入 Adapter 嵌套编辑模式
    用户双击黄色方块，进入内部工作流编辑
    """
    adapter_id = payload.get("adapter_id")
    
    adapter = adapter_registry.get(adapter_id)
    if not adapter or adapter.adapter_type != AdapterType.BLUEPRINT:
        return Message.create(
            "error",
            {"message": f"Adapter not found or not editable: {adapter_id}"},
            task_id=payload.get("task_id")
        )
    
    return Message.create(
        "adapter.edit_mode_entered",
        {
            "adapter_id": adapter_id,
            "name": adapter.name,
            "blueprint": adapter.blueprint_config.to_dict() if adapter.blueprint_config else None,
            "breadcrumbs": [adapter.name],  # 嵌套层级面包屑
            "can_add_child": True  # 是否可继续添加子 Adapter
        },
        task_id=payload.get("task_id")
    )


async def handle_adapter_execute(websocket, payload: dict, server) -> dict:
    """adapter.execute → 执行 Adapter"""
    task_id = payload.get("task_id")
    adapter_id = payload.get("adapter_id")
    
    adapter = adapter_registry.get(adapter_id)
    if not adapter:
        return Message.create(
            "error",
            {"message": f"Adapter not found: {adapter_id}"},
            task_id=task_id
        )
    
    # 异步执行（不阻塞 WebSocket）
    asyncio.create_task(_execute_adapter_async(adapter, task_id, server))
    
    return Message.create(
        "adapter.execution_started",
        {"adapter_id": adapter_id, "name": adapter.name},
        task_id=task_id
    )


async def _execute_adapter_async(adapter: Adapter, task_id: str, server):
    """异步执行 Adapter 并推送状态更新"""
    result = await adapter_execution_engine.execute(
        adapter,
        {"task_id": task_id},
        task_id
    )
    
    await server.broadcast_to_task(
        task_id,
        Message.create(
            "adapter.execution_completed",
            {
                "adapter_id": adapter.id,
                "name": adapter.name,
                "success": result.get("success"),
                "result": result.get("result"),
                "error": result.get("error"),
                "has_screenshots": "screenshots" in result  # 是否有工作区截图
            },
            task_id=task_id
        )
    )


async def handle_adapter_detach_from_step(websocket, payload: dict, server) -> dict:
    """adapter.detach_from_step → 从步骤解绑 Adapter"""
    task_id = payload.get("task_id")
    step_id = payload.get("step_id")
    adapter_id = payload.get("adapter_id")
    
    try:
        from backend.core.task_manager import task_manager
        
        task = task_manager.get_task(task_id)
        if not task or not task.execution_blueprint:
            return Message.create(
                "error",
                {"message": "Task or blueprint not found"},
                task_id=task_id
            )
        
        for step in task.execution_blueprint.steps:
            if step.id == step_id and hasattr(step, "attached_adapters"):
                step.attached_adapters = [
                    a for a in step.attached_adapters if a.adapter_id != adapter_id
                ]
                break
        
        return Message.create(
            "adapter.detached",
            {"step_id": step_id, "adapter_id": adapter_id},
            task_id=task_id
        )
        
    except ImportError:
        return Message.create(
            "adapter.detached",
            {"step_id": step_id, "adapter_id": adapter_id, "mock": True},
            task_id=task_id
        )


async def handle_adapter_clone(websocket, payload: dict, server) -> dict:
    """adapter.clone → 克隆 Adapter"""
    adapter_id = payload.get("adapter_id")
    new_name = payload.get("new_name")
    
    try:
        cloned = adapter_registry.clone(adapter_id, new_name)
        return Message.create(
            "adapter.cloned",
            _serialize_adapter(cloned),
            task_id=payload.get("task_id")
        )
    except ValueError as e:
        return Message.create(
            "error",
            {"message": str(e)},
            task_id=payload.get("task_id")
        )


async def handle_adapter_delete(websocket, payload: dict, server) -> dict:
    """adapter.delete → 删除 Adapter"""
    adapter_id = payload.get("adapter_id")
    
    success = adapter_registry.delete(adapter_id)
    
    if success:
        return Message.create(
            "adapter.deleted",
            {"adapter_id": adapter_id},
            task_id=payload.get("task_id")
        )
    else:
        return Message.create(
            "error",
            {"message": f"Cannot delete adapter (may be referenced by others): {adapter_id}"},
            task_id=payload.get("task_id")
        )
