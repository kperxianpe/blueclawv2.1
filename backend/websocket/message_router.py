#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Message Router - Complete implementation with all 8 handlers

Handlers:
1. task.start
2. thinking.select_option
3. thinking.custom_input  
4. thinking.confirm_execution
5. execution.start
6. execution.pause
7. execution.resume
8. execution.intervene
"""

import json
import asyncio
import uuid
from typing import Dict, Optional
from datetime import datetime

from backend.core.task_manager import task_manager
from backend.core.checkpoint import checkpoint_manager
from blueclaw.api.engine_facade import BlueclawEngineFacade
from blueclaw.core.thinking_engine import thinking_engine
from blueclaw.core.execution_engine import execution_engine
from blueclaw.core.state_sync import state_sync
from blueclaw.api.messages import Message

# Week 20 Vis-Adapter imports
from backend.vis import vms, vlm, mpl, hee
from backend.vis.hybrid_executor import ExecutionMode

# Week 20.5 Tool System imports
from backend.websocket.handlers.tools import handle_tools_list, handle_tools_inspect
from backend.websocket.handlers.nodes import handle_node_bind_tool, handle_node_unlock_tool
from backend.websocket.handlers.mcp import handle_mcp_execute, handle_mcp_refresh
from backend.websocket.handlers.sandbox import (
    handle_sandbox_execute, handle_sandbox_create, handle_sandbox_cleanup
)

# Week 20.6 Adapter System imports
from backend.websocket.handlers.adapter import (
    handle_adapter_list, handle_adapter_get, handle_adapter_create,
    handle_adapter_update, handle_adapter_add_input, handle_adapter_attach_to_step,
    handle_adapter_enter_edit, handle_adapter_execute, handle_adapter_detach_from_step,
    handle_adapter_clone, handle_adapter_delete
)

# Week 30.6 Adapter Runtime imports
from backend.websocket.handlers.adapter_runtime import (
    handle_adapter_blueprint_attach, handle_adapter_blueprint_detach,
    handle_adapter_runtime_start, handle_adapter_runtime_pause,
    handle_adapter_runtime_resume, handle_adapter_runtime_freeze,
    handle_adapter_runtime_unfreeze, handle_adapter_runtime_retry,
    handle_adapter_runtime_replan, handle_adapter_runtime_dismiss_annotation,
)
from backend.core.adapter_runtime_manager import adapter_runtime_manager


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        self.handlers = {
            # Task handlers
            "task.start": self._handle_task_start,
            "task.interrupt": self._handle_task_interrupt,
            
            # Thinking handlers
            "thinking.select_option": self._handle_thinking_select_option,
            "thinking.custom_input": self._handle_thinking_custom_input,
            "thinking.confirm_execution": self._handle_thinking_confirm_execution,
            
            # Execution handlers
            "execution.start": self._handle_execution_start,
            "execution.pause": self._handle_execution_pause,
            "execution.resume": self._handle_execution_resume,
            "execution.intervene": self._handle_execution_intervene,
            "execution.cancel": self._handle_execution_cancel,
            
            # Week 20 Vis-Adapter handlers
            "vis.preview": self._handle_vis_preview,
            "vis.user_selection": self._handle_vis_user_selection,
            "vis.confirm": self._handle_vis_confirm,
            "vis.skip": self._handle_vis_skip,
            "vis.batch_confirm": self._handle_vis_batch_confirm,
            "vis.action": self._handle_vis_action,
            
            # Week 20.5 Tool System handlers
            "tools.list": handle_tools_list,
            "tools.inspect": handle_tools_inspect,
            "node.bind_tool": handle_node_bind_tool,
            "node.unlock_tool": handle_node_unlock_tool,
            "mcp.execute": handle_mcp_execute,
            "mcp.refresh": handle_mcp_refresh,
            "sandbox.execute": handle_sandbox_execute,
            "sandbox.create": handle_sandbox_create,
            "sandbox.cleanup": handle_sandbox_cleanup,
            
            # Week 20.6 Adapter System handlers (Studio CRUD)
            "adapter.list": handle_adapter_list,
            "adapter.get": handle_adapter_get,
            "adapter.create": handle_adapter_create,
            "adapter.update": handle_adapter_update,
            "adapter.add_input": handle_adapter_add_input,
            "adapter.attach_to_step": handle_adapter_attach_to_step,
            "adapter.detach_from_step": handle_adapter_detach_from_step,
            "adapter.enter_edit": handle_adapter_enter_edit,
            "adapter.execute": handle_adapter_execute,
            "adapter.clone": handle_adapter_clone,
            "adapter.delete": handle_adapter_delete,

            # v2.5 Studio aliases (backward compatible)
            "adapter.studio.list": handle_adapter_list,
            "adapter.studio.get": handle_adapter_get,
            "adapter.studio.create": handle_adapter_create,
            "adapter.studio.update": handle_adapter_update,
            "adapter.studio.delete": handle_adapter_delete,
            "adapter.studio.clone": handle_adapter_clone,
            "adapter.studio.enter_edit": handle_adapter_enter_edit,

            # v2.5 Blueprint Binding
            "adapter.blueprint.attach": handle_adapter_blueprint_attach,
            "adapter.blueprint.detach": handle_adapter_blueprint_detach,

            # v2.5 Runtime Control
            "adapter.runtime.start": handle_adapter_runtime_start,
            "adapter.runtime.pause": handle_adapter_runtime_pause,
            "adapter.runtime.resume": handle_adapter_runtime_resume,
            "adapter.runtime.freeze": handle_adapter_runtime_freeze,
            "adapter.runtime.unfreeze": handle_adapter_runtime_unfreeze,
            "adapter.runtime.retry": handle_adapter_runtime_retry,
            "adapter.runtime.replan": handle_adapter_runtime_replan,
            "adapter.runtime.dismiss_annotation": handle_adapter_runtime_dismiss_annotation,

            # V2 Frontend API aliases
            "user_input": self._handle_v2_user_input,
            "select_option": self._handle_v2_select_option,
            "custom_input": self._handle_v2_custom_input,
            
            # Week 30.5 Intervention / Freeze aliases (align with api_specification.md)
            "freeze_request": self._handle_freeze_request,
            "submit_annotation": self._handle_submit_annotation,
            "retry_step": self._handle_retry_step,
            "request_replan": self._handle_request_replan,
            "confirm_replan": self._handle_confirm_replan,
        }
        self.facades: Dict[str, BlueclawEngineFacade] = {}
    
    def set_websocket_server(self, server):
        state_sync.set_websocket_server(server)
        adapter_runtime_manager.set_websocket_server(server)
    
    def _get_task_id(self, websocket, server) -> Optional[str]:
        """Infer task_id from websocket connection."""
        if hasattr(server, 'get_task_id_for_connection'):
            return server.get_task_id_for_connection(websocket)
        if hasattr(server, 'connections') and websocket in server.connections:
            conn_info = server.connections[websocket]
            if isinstance(conn_info, dict):
                return conn_info.get("task_id") or None
        return None
    
    async def route(self, websocket, message: dict, server) -> dict:
        """路由消息到对应处理器"""
        msg_type = message.get("type", "unknown")
        payload = message.get("payload", {})
        
        # Auto-infer task_id from connection if not provided (V2 frontend compatibility)
        if isinstance(payload, dict):
            task_id = payload.get("task_id", "")
            if not task_id:
                conn_task_id = self._get_task_id(websocket, server)
                if conn_task_id:
                    payload = {**payload, "task_id": conn_task_id}
        
        handler = self.handlers.get(msg_type)
        if handler:
            return await handler(websocket, payload, server)
        
        return {"type": "error", "error": f"Unknown message type: {msg_type}"}
    
    # ========== V2 API Adapters ==========
    
    async def _handle_v2_user_input(self, websocket, payload: dict, server) -> dict:
        """V2 API adapter: user_input -> task.start"""
        v2_input = payload.get("input", "")
        adapted_payload = {"user_input": v2_input}
        if payload.get("task_id"):
            adapted_payload["task_id"] = payload["task_id"]
        return await self._handle_task_start(websocket, adapted_payload, server)
    
    async def _handle_v2_select_option(self, websocket, payload: dict, server) -> dict:
        """V2 API adapter: select_option -> thinking.select_option"""
        adapted_payload = {
            "current_node_id": payload.get("nodeId", ""),
            "option_id": payload.get("optionId", ""),
        }
        if payload.get("task_id"):
            adapted_payload["task_id"] = payload["task_id"]
        return await self._handle_thinking_select_option(websocket, adapted_payload, server)
    
    async def _handle_v2_custom_input(self, websocket, payload: dict, server) -> dict:
        """V2 API adapter: custom_input -> thinking.custom_input"""
        adapted_payload = {
            "current_node_id": payload.get("nodeId", ""),
            "custom_input": payload.get("input", ""),
        }
        if payload.get("task_id"):
            adapted_payload["task_id"] = payload["task_id"]
        return await self._handle_thinking_custom_input(websocket, adapted_payload, server)
    
    # ========== Task Handlers ==========
    
    async def _handle_task_start(self, websocket, payload: dict, server) -> dict:
        """Handler 1: 任务启动"""
        user_input = payload.get("user_input", "")
        
        # 1. 创建任务
        task = await task_manager.create_task(user_input)
        
        # 2. 关联连接与任务
        server.associate_connection_with_task(websocket, task.id)
        
        # 3. 创建 EngineFacade
        facade = BlueclawEngineFacade(task.id)
        self.facades[task.id] = facade
        
        # 4. 调用思考引擎开始思考
        root_node = await thinking_engine.start_thinking(task.id, user_input)
        
        # 5. 推送思考节点
        if root_node:
            await state_sync.push_thinking_node_created(task.id, root_node, is_root=True)
        
        return Message.task_started(task.id, user_input)
    
    async def _handle_task_interrupt(self, websocket, payload: dict, server) -> dict:
        """处理任务中断"""
        task_id = payload.get("task_id", "")
        # 实现任务中断逻辑
        return {"type": "task.interrupted", "payload": {"task_id": task_id}}
    
    # ========== Thinking Handlers ==========
    
    async def _auto_generate_blueprint(self, task_id: str, final_path: list) -> None:
        """思考收敛后自动生成蓝图并广播"""
        try:
            print(f"[AutoBlueprint] Auto-generating blueprint for task {task_id}")
            await state_sync.push_thinking_converged(task_id, final_path)
            
            # 更新任务状态
            await task_manager.update_task_status(task_id, "EXECUTING")
            
            # 生成执行蓝图
            blueprint = await execution_engine.create_blueprint(task_id, final_path)
            print(f"[AutoBlueprint] Blueprint created: {blueprint.id} with {len(blueprint.steps)} steps")
            
            # 推送蓝图加载
            await state_sync.push_execution_blueprint_loaded(task_id, blueprint)
            
            # 自动开始执行
            asyncio.create_task(execution_engine.start_execution(blueprint.id))
            print(f"[AutoBlueprint] Auto-started execution for blueprint {blueprint.id}")
        except Exception as e:
            print(f"[AutoBlueprint] Error auto-generating blueprint: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_thinking_select_option(self, websocket, payload: dict, server) -> dict:
        """Handler 2: 选择思考选项"""
        task_id = payload.get("task_id", "")
        option_id = payload.get("option_id", "")
        current_node_id = payload.get("current_node_id", "")
        
        print(f"[DEBUG router] select_option called: task={task_id}, node={current_node_id}, option={option_id}")
        
        if not task_id or not option_id:
            return {"type": "error", "error": "Missing task_id or option_id"}
        
        # 1. 选择选项并获取下一层
        result = await thinking_engine.select_option(
            task_id=task_id,
            node_id=current_node_id,
            option_id=option_id
        )
        print(f"[DEBUG router] select_option result: has_more={result.get('has_more_options')}, converged={result.get('converged')}")
        
        # 2. 保存checkpoint
        await checkpoint_manager.save_checkpoint(task_manager.get_task(task_id))
        
        # 3. 推送节点更新
        if result.get("has_more_options"):
            # 还有下一层，推送新选项
            next_node = result.get("next_node")
            await state_sync.push_thinking_node_created(task_id, next_node, is_root=False)
            return Message.thinking_option_selected(task_id, option_id, has_more=True, current_node_id=current_node_id)
        else:
            # 收敛完成，自动生成蓝图并广播
            final_path = result.get("final_path", [])
            await state_sync.push_thinking_completed(task_id, final_path)
            asyncio.create_task(self._auto_generate_blueprint(task_id, final_path))
            return Message.thinking_option_selected(task_id, option_id, has_more=False, final_path=final_path, current_node_id=current_node_id)
    
    async def _handle_thinking_custom_input(self, websocket, payload: dict, server) -> dict:
        """Handler 3: 自定义输入（第4个白块）"""
        task_id = payload.get("task_id", "")
        custom_input = payload.get("custom_input", "")
        current_node_id = payload.get("current_node_id", "")
        
        if not task_id or not custom_input:
            return {"type": "error", "error": "Missing task_id or custom_input"}
        
        # 1. 使用自定义输入继续思考
        result = await thinking_engine.select_custom_input(
            task_id=task_id,
            node_id=current_node_id,
            custom_input=custom_input
        )
        
        # 2. 保存checkpoint
        await checkpoint_manager.save_checkpoint(task_manager.get_task(task_id))
        
        # 3. 推送节点更新
        if result.get("has_more_options"):
            next_node = result.get("next_node")
            await state_sync.push_thinking_node_created(task_id, next_node, is_root=False)
            return Message.thinking_custom_input_received(task_id, has_more=True, current_node_id=current_node_id, custom_input=custom_input)
        else:
            final_path = result.get("final_path", [])
            await state_sync.push_thinking_completed(task_id, final_path)
            asyncio.create_task(self._auto_generate_blueprint(task_id, final_path))
            return Message.thinking_custom_input_received(task_id, has_more=False, final_path=final_path, current_node_id=current_node_id, custom_input=custom_input)
    
    async def _handle_thinking_confirm_execution(self, websocket, payload: dict, server) -> dict:
        """Handler 4: 确认执行（兼容自动蓝图模式：如果已有蓝图则复用）"""
        task_id = payload.get("task_id", "")
        
        # 1. 检查是否已有蓝图（自动收敛时可能已经生成）
        existing_blueprint = execution_engine.get_blueprint_by_task_id(task_id)
        if existing_blueprint:
            print(f"[ConfirmExecution] Reusing existing blueprint {existing_blueprint.id} for task {task_id}")
            await state_sync.push_execution_blueprint_loaded(task_id, existing_blueprint)
            return Message.thinking_execution_confirmed(
                task_id, existing_blueprint.id,
                existing_blueprint.to_dict() if hasattr(existing_blueprint, 'to_dict') else {}
            )
        
        # 2. 获取最终思考路径
        final_path = thinking_engine.get_final_path(task_id)
        
        # 3. 更新任务状态
        await task_manager.update_task_status(task_id, "EXECUTING")
        
        # 4. 生成执行蓝图
        blueprint = await execution_engine.create_blueprint(task_id, final_path)
        
        # 5. 推送蓝图加载
        await state_sync.push_execution_blueprint_loaded(task_id, blueprint)
        
        # 6. 自动开始执行
        print(f"[ConfirmExecution] Auto-starting execution for blueprint {blueprint.id}")
        asyncio.create_task(execution_engine.start_execution(blueprint.id))
        
        return Message.thinking_execution_confirmed(task_id, blueprint.id, blueprint.to_dict() if hasattr(blueprint, 'to_dict') else {})
    
    # ========== Execution Handlers ==========
    
    async def _handle_execution_start(self, websocket, payload: dict, server) -> dict:
        """Handler 5: 开始执行"""
        task_id = payload.get("task_id", "")
        blueprint_id = payload.get("blueprint_id", "")
        
        print(f"[ExecutionStart] task_id={task_id}, provided_blueprint_id={blueprint_id}")
        
        if not task_id:
            return {"type": "error", "error": "Missing task_id"}
        
        # 如果没有 blueprint_id，通过 task_id 查找
        if not blueprint_id:
            blueprint = execution_engine.get_blueprint_by_task_id(task_id)
            if blueprint:
                blueprint_id = blueprint.id
                print(f"[ExecutionStart] Found blueprint by task_id: {blueprint_id}")
            else:
                print(f"[ExecutionStart] No blueprint found for task_id. Available tasks: {[b.task_id for b in execution_engine.blueprints.values()]}")
        
        if not blueprint_id:
            return {"type": "error", "error": "Missing blueprint_id and no blueprint found for task"}
        
        # 启动执行
        success = await execution_engine.start_execution(blueprint_id)
        print(f"[ExecutionStart] start_execution returned: {success}")
        
        if success:
            return Message.execution_started(task_id, blueprint_id)
        else:
            return {"type": "error", "error": "Failed to start execution"}
    
    async def _handle_execution_pause(self, websocket, payload: dict, server) -> dict:
        """Handler 6: 暂停执行"""
        task_id = payload.get("task_id", "")
        blueprint_id = payload.get("blueprint_id", "")
        
        if blueprint_id:
            await execution_engine.pause_execution(blueprint_id)
            await state_sync.push_execution_paused(task_id, blueprint_id)
            return Message.execution_paused(task_id, blueprint_id)
        
        return {"type": "error", "error": "Missing blueprint_id"}
    
    async def _handle_execution_resume(self, websocket, payload: dict, server) -> dict:
        """Handler 7: 恢复执行"""
        task_id = payload.get("task_id", "")
        blueprint_id = payload.get("blueprint_id", "")
        
        if blueprint_id:
            success = await execution_engine.resume_execution(blueprint_id)
            if success:
                await state_sync.push_execution_resumed(task_id, blueprint_id)
                return Message.execution_resumed(task_id, blueprint_id)
            else:
                return {"type": "error", "error": "Execution not in paused state"}
        
        return {"type": "error", "error": "Missing blueprint_id"}
    
    async def _handle_execution_cancel(self, websocket, payload: dict, server) -> dict:
        """取消指定蓝图的执行（测试/清理用）"""
        task_id = payload.get("task_id", "")
        blueprint_id = payload.get("blueprint_id", "")
        
        if not blueprint_id:
            return {"type": "error", "error": "Missing blueprint_id"}
        
        print(f"[ExecutionCancel] Cancelling execution for blueprint {blueprint_id}")
        execution_engine.cancel_execution(blueprint_id)
        
        return {
            "type": "execution.cancelled",
            "payload": {
                "task_id": task_id,
                "blueprint_id": blueprint_id
            }
        }
    
    async def _handle_execution_intervene(self, websocket, payload: dict, server) -> dict:
        """Handler 8: 用户干预"""
        task_id = payload.get("task_id", "")
        blueprint_id = payload.get("blueprint_id", "")
        step_id = payload.get("step_id", "")
        action = payload.get("action", "")  # replan, skip, retry, modify
        custom_input = payload.get("custom_input", "")
        
        if not all([blueprint_id, step_id, action]):
            return {"type": "error", "error": "Missing required parameters"}
        
        # REPLAN 特殊处理：返回思考阶段重新生成选项
        if action == "replan":
            blueprint = execution_engine.blueprints.get(blueprint_id)
            if not blueprint:
                return {"type": "error", "error": "Blueprint not found"}
            
            # 先取消旧蓝图的执行，避免残留 step task 占用资源
            execution_engine.cancel_execution(blueprint_id)
            
            # 收集已完成步骤摘要
            completed_summaries = []
            for s in blueprint.steps:
                status_val = s.status.value if hasattr(s.status, 'value') else str(s.status)
                if status_val == "completed":
                    completed_summaries.append(f"{s.name}: {s.result or '完成'}")
            completed_summary = "; ".join(completed_summaries) if completed_summaries else "无"
            
            # 标记干预步骤及后续步骤为废弃
            archived_ids = []
            found = False
            for s in blueprint.steps:
                if s.id == step_id:
                    found = True
                if found:
                    archived_ids.append(s.id)
                    # 尽量标记为 deprecated（如果 StepStatus 可用）
                    try:
                        from blueclaw.core.execution_engine import StepStatus
                        s.status = StepStatus.DEPRECATED
                    except Exception:
                        pass
            
            # 获取原始任务输入
            task = task_manager.get_task(task_id)
            original_input = task.user_input if task else ""
            
            # 重启思考流程
            new_root_node = await thinking_engine.restart_thinking_from_intervention(
                task_id=task_id,
                original_input=original_input,
                completed_summary=completed_summary,
                intervention_input=custom_input or "用户希望重新规划后续执行"
            )
            
            # 推送返回思考阶段消息
            await state_sync.push_execution_returned_to_thinking(task_id, archived_ids)
            
            # 推送新的思考根节点
            await state_sync.push_thinking_node_created(task_id, new_root_node, is_root=True)
            
            return Message.execution_intervened(task_id, blueprint_id, step_id, action, {
                "returned_to_thinking": True,
                "new_node_id": new_root_node.id
            })
        
        # 构建干预数据
        intervention_data = {}
        if custom_input:
            intervention_data["custom_input"] = custom_input
        if "direction" in payload:
            intervention_data["direction"] = payload["direction"]
        
        # 执行干预（非 replan）
        result = await execution_engine.handle_intervention(
            blueprint_id=blueprint_id,
            step_id=step_id,
            action=action,
            data=intervention_data
        )
        
        return Message.execution_intervened(task_id, blueprint_id, step_id, action, result or {})
    
    # ========== Week 20 Vis-Adapter Handlers ==========
    
    async def _handle_vis_preview(self, websocket, payload: dict, server) -> dict:
        """
        vis.preview -> 请求视觉预览
        后端截图并通过 WebSocket 推送
        """
        task_id = payload.get("task_id", "")
        region = payload.get("region")  # 可选: {"x", "y", "width", "height"}
        task_description = payload.get("task_description", "")
        
        if not task_id:
            return {"type": "error", "error": "Missing task_id"}
        
        # 截图
        if region:
            screenshot = await vms.capture_region(
                task_id, int(region["x"]), int(region["y"]), 
                int(region["width"]), int(region["height"])
            )
        else:
            screenshot = await vms.capture_fullscreen(task_id)
        
        if screenshot:
            # 分析截图
            analysis = await vlm.analyze_screenshot(
                screenshot.base64,
                task_description
            )
            
            # 推送视觉反馈
            await state_sync.push_visual_preview(task_id, screenshot, analysis)
            
            return {
                "type": "vis.preview_ready",
                "payload": {
                    "screenshot_id": screenshot.id,
                    "width": screenshot.width,
                    "height": screenshot.height,
                    "elements_count": len(analysis.get("elements", [])),
                    "analysis": {
                        "scene_type": analysis.get("scene_type"),
                        "suggested_next_action": analysis.get("suggested_next_action")
                    }
                }
            }
        
        return {"type": "error", "error": "Screenshot failed"}
    
    async def _handle_vis_user_selection(self, websocket, payload: dict, server) -> dict:
        """
        vis.user_selection -> 用户圈选反馈
        前端用户圈选了某个区域，后端接收坐标并分析
        """
        task_id = payload.get("task_id", "")
        screenshot_id = payload.get("screenshot_id", "")
        selection = payload.get("selection", {})  # {"x", "y", "width", "height"}
        
        screenshot = vms.get_screenshot(screenshot_id)
        if not screenshot:
            return {"type": "error", "error": "Screenshot not found"}
        
        # 在截图上添加用户圈选标注
        vms.add_annotation(
            screenshot_id,
            "rect",
            selection,
            label="用户圈选",
            color="#FF6B35"
        )
        
        # 对圈选区域进行详细分析
        region_screenshot = await vms.capture_region(
            task_id,
            int(selection.get("x", 0)),
            int(selection.get("y", 0)),
            int(selection.get("width", 100)),
            int(selection.get("height", 100))
        )
        
        if region_screenshot:
            analysis = await vlm.analyze_screenshot(
                region_screenshot.base64,
                "分析用户圈选的区域"
            )
            
            return {
                "type": "vis.selection_analyzed",
                "payload": {
                    "selection": selection,
                    "analysis": analysis,
                    "region_screenshot_id": region_screenshot.id
                }
            }
        
        return {"type": "error", "error": "Region analysis failed"}
    
    async def _handle_vis_confirm(self, websocket, payload: dict, server) -> dict:
        """
        vis.confirm -> 确认视觉识别结果并执行
        """
        task_id = payload.get("task_id", "")
        screenshot_id = payload.get("screenshot_id", "")
        action = payload.get("action", "click")  # click, double_click, drag, etc.
        
        result = None
        
        if action == "click":
            x = payload.get("x", 0)
            y = payload.get("y", 0)
            result = await mpl.click(x, y)
        elif action == "double_click":
            x = payload.get("x", 0)
            y = payload.get("y", 0)
            result = await mpl.double_click(x, y)
        elif action == "right_click":
            x = payload.get("x", 0)
            y = payload.get("y", 0)
            result = await mpl.right_click(x, y)
        elif action == "drag":
            result = await mpl.drag(
                payload.get("start_x", 0),
                payload.get("start_y", 0),
                payload.get("end_x", 0),
                payload.get("end_y", 0)
            )
        elif action == "type":
            result = await mpl.type_text(payload.get("text", ""))
        elif action == "keypress":
            result = await mpl.keypress(payload.get("keys", []))
        
        return {
            "type": "vis.action_executed",
            "payload": {
                "action": action,
                "result": result.to_dict() if result else None
            }
        }
    
    async def _handle_vis_skip(self, websocket, payload: dict, server) -> dict:
        """
        vis.skip -> 跳过当前视觉步骤
        """
        task_id = payload.get("task_id", "")
        
        return {
            "type": "vis.skipped",
            "payload": {"message": "Visual step skipped", "task_id": task_id}
        }
    
    async def _handle_vis_batch_confirm(self, websocket, payload: dict, server) -> dict:
        """
        vis.batch_confirm -> 批量确认多个操作
        """
        task_id = payload.get("task_id", "")
        actions = payload.get("actions", [])  # [{"action": "click", "x": ..., "y": ...}, ...]
        
        results = await hee.execute_action_sequence(task_id, actions)
        
        return {
            "type": "vis.batch_executed",
            "payload": results
        }
    
    async def _handle_vis_action(self, websocket, payload: dict, server) -> dict:
        """
        vis.action -> 执行单个视觉动作（简化接口）
        """
        task_id = payload.get("task_id", "")
        action_def = payload.get("action_def", {})
        
        result = await mpl.execute_action(action_def)
        
        return {
            "type": "vis.action_result",
            "payload": {
                "action": action_def.get("action"),
                "result": result.to_dict()
            }
        }
    
    # ── Week 30.5 Intervention / Freeze handlers (full business logic) ──

    async def _handle_freeze_request(self, websocket, payload: dict, server) -> dict:
        """freeze_request — 用户请求冻结当前步骤
        1. 查找 blueprint  2. 截图  3. 冻结 runtime  4. 推送 freeze.confirmed
        """
        task_id = payload.get("task_id", "")
        step_id = payload.get("step_id", "")
        reason = payload.get("reason", "用户请求冻结")

        if not task_id:
            return Message.create("error", {"message": "Missing task_id"}, task_id=task_id)

        blueprint = execution_engine.get_blueprint_by_task_id(task_id)
        if not blueprint:
            return Message.create("error", {"message": f"Blueprint not found for task {task_id}"}, task_id=task_id)

        blueprint_id = blueprint.id

        # 确保 runtime 存在（如果不存在则自动创建）
        if not adapter_runtime_manager.get(blueprint_id):
            adapter_runtime_manager.attach(blueprint_id, task_id, f"studio_{blueprint_id[:8]}", "web")
            print(f"[freeze_request] Runtime auto-attached for {blueprint_id}")

        # 截图（延迟导入避免循环依赖）
        screenshot_b64 = ""
        try:
            from blueclaw.adapter.manager import AdapterManager
            mgr = AdapterManager()
            # FIX: 如果 task_id 未注册，尝试自动初始化 WebAdapter
            if task_id not in getattr(mgr, '_task_adapter_map', {}):
                try:
                    from blueclaw.adapter.models import ExecutionBlueprint as AdapterBP
                    adapter_bp = AdapterBP(
                        task_id=task_id,
                        adapter_type="web",
                        steps=[],
                        config={"extra": {"viewport": {"width": 1280, "height": 720}}}
                    )
                    adapter = mgr.get_adapter("web")
                    if getattr(adapter, '_page', None) is None:
                        await adapter.init(adapter_bp)
                        print(f"[freeze_request] WebAdapter auto-initialized for {task_id}")
                    mgr._task_adapter_map[task_id] = "web"
                except Exception as init_e:
                    print(f"[freeze_request] WebAdapter auto-init skipped: {init_e}")
            screenshot_b64 = await mgr.screenshot(task_id)
        except Exception as e:
            print(f"[freeze_request] Screenshot error: {e}")

        freeze_token = f"freeze_{uuid.uuid4().hex[:12]}"

        # 冻结 runtime 状态
        adapter_runtime_manager.set_state(blueprint_id, "frozen")
        await adapter_runtime_manager.push_frozen(blueprint_id, reason)
        await adapter_runtime_manager.push_state(blueprint_id)

        # 推送 freeze.confirmed（前端据此显示冻结覆盖层）
        await state_sync.push_freeze_confirmed(task_id, step_id, screenshot_b64, freeze_token)

        return Message.create(
            "freeze.request_ack",
            {"step_id": step_id, "freeze_token": freeze_token, "screenshot": bool(screenshot_b64)},
            task_id=task_id,
        )

    async def _handle_submit_annotation(self, websocket, payload: dict, server) -> dict:
        """submit_annotation — 用户提交标注并请求解冻
        1. 查找 blueprint  2. 保存标注（boxes + text） 3. 恢复 runtime  4. 推送解冻通知  5. 恢复 ExecutionEngine
        """
        task_id = payload.get("task_id", "")
        step_id = payload.get("step_id", "")
        annotation = payload.get("annotation", "")
        boxes = payload.get("boxes", []) or []
        freeze_token = payload.get("freeze_token", "")

        if not task_id:
            return Message.create("error", {"message": "Missing task_id"}, task_id=task_id)

        blueprint = execution_engine.get_blueprint_by_task_id(task_id)
        if not blueprint:
            return Message.create("error", {"message": f"Blueprint not found for task {task_id}"}, task_id=task_id)

        blueprint_id = blueprint.id

        # 确保 runtime 存在（如果不存在则自动创建）
        if not adapter_runtime_manager.get(blueprint_id):
            adapter_runtime_manager.attach(blueprint_id, task_id, f"studio_{blueprint_id[:8]}", "web")
            print(f"[submit_annotation] Runtime auto-attached for {blueprint_id}")

        # 保存文本标注
        if annotation:
            adapter_runtime_manager.add_annotation(
                blueprint_id, "info", annotation, step_id=step_id
            )

        # 保存框选标注
        saved_boxes = []
        for box in boxes:
            rect = {
                "x": box.get("x", 0),
                "y": box.get("y", 0),
                "w": box.get("w", 0),
                "h": box.get("h", 0),
            }
            label = box.get("label", "")
            ann = adapter_runtime_manager.add_annotation(
                blueprint_id, "freeze",
                f"用户标注: {label}" if label else "用户框选标注",
                rect=rect, step_id=step_id
            )
            if ann:
                saved_boxes.append({"id": ann.id, "rect": rect, "label": label})

        # 恢复 runtime 状态
        adapter_runtime_manager.set_state(blueprint_id, "running")
        await adapter_runtime_manager.push_unfrozen(blueprint_id)
        await adapter_runtime_manager.push_state(blueprint_id)

        # 推送状态更新
        await state_sync.push_status_update(task_id, {
            "status": "resumed",
            "step_id": step_id,
            "annotation": annotation,
            "boxes_count": len(saved_boxes),
            "message": f"用户提交标注（{len(saved_boxes)} 个框），执行恢复",
        })

        # 恢复执行引擎
        try:
            await execution_engine.resume_execution(blueprint_id)
        except Exception as e:
            print(f"[submit_annotation] Resume error: {e}")

        return Message.create(
            "annotation.submitted",
            {
                "step_id": step_id,
                "annotation": annotation,
                "boxes": saved_boxes,
                "freeze_token": freeze_token,
            },
            task_id=task_id,
        )

    async def _handle_retry_step(self, websocket, payload: dict, server) -> dict:
        """retry_step — 用户请求重新执行当前步骤
        1. 查找 blueprint  2. 调用 ExecutionEngine.handle_intervention(retry)
        3. 添加 annotation  4. 推送状态更新
        """
        task_id = payload.get("task_id", "")
        step_id = payload.get("step_id", "")
        reason = payload.get("reason", "用户请求重新执行")

        if not task_id:
            return Message.create("error", {"message": "Missing task_id"}, task_id=task_id)

        blueprint = execution_engine.get_blueprint_by_task_id(task_id)
        if not blueprint:
            return Message.create("error", {"message": f"Blueprint not found for task {task_id}"}, task_id=task_id)

        blueprint_id = blueprint.id

        # 调用 ExecutionEngine 干预逻辑（重置步骤 + 恢复执行）
        result = await execution_engine.handle_intervention(blueprint_id, step_id, "retry")
        if not result:
            return Message.create("error", {"message": f"Failed to retry step {step_id}"}, task_id=task_id)

        # 添加 runtime annotation
        adapter_runtime_manager.add_annotation(
            blueprint_id, "info", f"Retry requested: {reason}", step_id=step_id
        )
        await adapter_runtime_manager.push_state(blueprint_id)

        # 推送状态更新
        await state_sync.push_status_update(task_id, {
            "status": "retrying",
            "step_id": step_id,
            "reason": reason,
        })

        return Message.create(
            "retry.step_ack",
            {"step_id": step_id, "reason": reason},
            task_id=task_id,
        )

    async def _handle_request_replan(self, websocket, payload: dict, server) -> dict:
        """request_replan — 用户请求从当前步骤重新规划
        1. 查找 blueprint  2. 调用 ExecutionEngine.handle_intervention(replan)
        3. 推送 replan.result
        """
        task_id = payload.get("task_id", "")
        step_id = payload.get("step_id", "")
        reason = payload.get("reason", "用户请求重新规划")

        if not task_id:
            return Message.create("error", {"message": "Missing task_id"}, task_id=task_id)

        blueprint = execution_engine.get_blueprint_by_task_id(task_id)
        if not blueprint:
            return Message.create("error", {"message": f"Blueprint not found for task {task_id}"}, task_id=task_id)

        blueprint_id = blueprint.id

        # 调用 ExecutionEngine 干预逻辑（重新规划 + 恢复执行）
        result = await execution_engine.handle_intervention(
            blueprint_id, step_id, "replan", {"custom_input": reason}
        )
        if not result:
            return Message.create("error", {"message": f"Failed to replan from step {step_id}"}, task_id=task_id)

        new_steps = result.get("new_steps", [])

        # 推送 replan.result（前端据此显示新蓝图供用户确认）
        await state_sync.push_replan_result(task_id, accepted=True, new_steps=new_steps, reason=reason)

        return Message.create(
            "replan.request_ack",
            {"step_id": step_id, "reason": reason, "new_steps_count": len(new_steps)},
            task_id=task_id,
        )

    async def _handle_confirm_replan(self, websocket, payload: dict, server) -> dict:
        """confirm_replan — 用户确认或拒绝重新规划结果
        accept=True: 切换到 running 状态，恢复执行
        accept=False: 保持 paused 状态
        """
        task_id = payload.get("task_id", "")
        blueprint_id = payload.get("blueprint_id", "")
        step_id = payload.get("step_id", "")
        accept = payload.get("accept", False)

        if not task_id:
            return Message.create("error", {"message": "Missing task_id"}, task_id=task_id)

        # 若前端未传 blueprint_id，尝试查找
        if not blueprint_id:
            blueprint = execution_engine.get_blueprint_by_task_id(task_id)
            if blueprint:
                blueprint_id = blueprint.id

        if not blueprint_id:
            return Message.create("error", {"message": f"Blueprint not found for task {task_id}"}, task_id=task_id)

        if accept:
            # 接受新规划，切换到 running 状态并恢复执行
            adapter_runtime_manager.set_state(blueprint_id, "running")
            await adapter_runtime_manager.push_state(blueprint_id)

            try:
                await execution_engine.resume_execution(blueprint_id)
            except Exception as e:
                print(f"[confirm_replan] Resume error: {e}")

            await state_sync.push_status_update(task_id, {
                "status": "replan_accepted",
                "blueprint_id": blueprint_id,
            })

            return Message.create(
                "replan.confirmed",
                {"accepted": True, "blueprint_id": blueprint_id},
                task_id=task_id,
            )
        else:
            # 拒绝新规划，保持 paused 状态
            adapter_runtime_manager.set_state(blueprint_id, "paused")
            await adapter_runtime_manager.push_state(blueprint_id)

            await state_sync.push_status_update(task_id, {
                "status": "replan_rejected",
                "blueprint_id": blueprint_id,
            })

            return Message.create(
                "replan.confirmed",
                {"accepted": False, "blueprint_id": blueprint_id},
                task_id=task_id,
            )


# Global router instance
router = MessageRouter()
