#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter 执行引擎
支持递归执行、多模态输入处理、循环检测
"""
from typing import Dict, List, Any, Optional, Set
import asyncio
import time

from .models import (
    Adapter, AdapterType, AdapterLevel, 
    MultimodalInput, BlueprintStep, adapter_registry
)


class AdapterExecutionEngine:
    """
    Adapter 执行引擎
    
    核心能力：
    1. 递归执行嵌套 Adapter
    2. 多模态输入处理（含工具/Adapter作为模态）
    3. 循环引用检测
    4. Agent 协作编排
    """
    
    # 限制常量
    MAX_DEPTH = 5  # 最大嵌套层级
    TIMEOUT = 300  # 5分钟超时
    MAX_CONCURRENT = 5  # 最大并发
    
    def __init__(self):
        self._execution_stack: List[str] = []  # 防循环
        self._running_tasks: Dict[str, bool] = {}  # 任务状态
        self._execution_count: Dict[str, int] = {}  # 执行计数
    
    async def execute(
        self,
        adapter: Adapter,
        context: Dict[str, Any],
        task_id: str
    ) -> Dict[str, Any]:
        """
        执行 Adapter
        
        Args:
            adapter: 要执行的 Adapter
            context: 执行上下文（含多模态输入）
            task_id: 任务 ID
        
        Returns:
            执行结果
        """
        # 循环检测
        if adapter.id in self._execution_stack:
            return {
                "success": False,
                "error": f"Circular reference detected: {adapter.id}",
                "error_type": "circular_reference"
            }
        
        # 深度限制
        if len(self._execution_stack) >= self.MAX_DEPTH:
            return {
                "success": False,
                "error": f"Max nesting depth exceeded: {self.MAX_DEPTH}",
                "error_type": "max_depth_exceeded"
            }
        
        self._execution_stack.append(adapter.id)
        self._execution_count[adapter.id] = self._execution_count.get(adapter.id, 0) + 1
        
        try:
            # 推送开始状态
            await self._push_status(task_id, adapter.id, "running")
            
            # 处理多模态输入（含工具/Adapter模态）
            processed_inputs = await self._process_multimodal_inputs(
                adapter.inputs, context, task_id
            )
            context["adapter_inputs"] = processed_inputs
            
            # 根据类型执行
            if adapter.adapter_type == AdapterType.SINGLE:
                result = await self._execute_single(adapter, context, task_id)
            elif adapter.adapter_type == AdapterType.BLUEPRINT:
                result = await self._execute_blueprint(adapter, context, task_id)
            elif adapter.adapter_type == AdapterType.AGENT:
                result = await self._execute_agent(adapter, context, task_id)
            elif adapter.adapter_type == AdapterType.REFERENCE:
                result = await self._execute_reference(adapter, context, task_id)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown adapter type: {adapter.adapter_type}"
                }
            
            # 推送完成状态
            status = "completed" if result.get("success") else "failed"
            await self._push_status(task_id, adapter.id, status, result)
            
            return result
            
        except Exception as e:
            error_result = {"success": False, "error": str(e), "error_type": "exception"}
            await self._push_status(task_id, adapter.id, "failed", error_result)
            return error_result
        finally:
            self._execution_stack.pop()
    
    async def _process_multimodal_inputs(
        self,
        inputs: List[MultimodalInput],
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """
        处理多模态输入
        支持传统模态 + 工具模态 + Adapter模态
        """
        processed = {
            "images": [],
            "videos": [],
            "audios": [],
            "files": [],
            "texts": [],
            "tools": [],      # 工具模态
            "adapters": [],   # Adapter模态
            "combined": []
        }
        
        for inp in inputs:
            item = {"type": inp.type, "data": inp.source, "metadata": inp.metadata}
            
            if inp.type == "image":
                processed["images"].append(item)
            elif inp.type == "video":
                processed["videos"].append(item)
            elif inp.type == "audio":
                processed["audios"].append(item)
            elif inp.type == "file":
                processed["files"].append(item)
            elif inp.type == "text":
                processed["texts"].append(inp.source)
            elif inp.type in ["tool", "skill"]:
                # 工具模态：需要解析并执行
                tool_result = await self._execute_tool_input(inp, context, task_id)
                processed["tools"].append({
                    "input": item,
                    "result": tool_result
                })
            elif inp.type == "adapter":
                # Adapter模态：递归执行引用的 Adapter
                ref_adapter = self._get_adapter_input(inp.ref_id)
                if ref_adapter:
                    adapter_result = await self.execute(ref_adapter, context, task_id)
                    processed["adapters"].append({
                        "input": item,
                        "result": adapter_result
                    })
            
            processed["combined"].append(item)
        
        return processed
    
    async def _execute_single(
        self,
        adapter: Adapter,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """执行单工具 Adapter"""
        config = adapter.single_config
        
        if not config:
            return {"success": False, "error": "No single_config found"}
        
        # 映射多模态输入到参数
        parameters = self._map_inputs_to_parameters(
            config.parameters,
            config.input_mapping,
            context.get("adapter_inputs", {})
        )
        
        # 根据工具类型调用
        if config.tool_type == "adapter-viser":
            # 调用视觉控制（用户感知为"工作区执行"）
            return await self._execute_adapter_viser(config, parameters, context, task_id)
        else:
            # 调用普通工具
            try:
                from backend.tools.registry import tool_registry
                return await tool_registry.execute_tool(
                    tool_id=config.tool_id,
                    context={"task_id": task_id, **context},
                    parameters=parameters
                )
            except ImportError:
                # Mock 模式
                return {
                    "success": True,
                    "result": f"[MOCK] Executed {config.tool_type}:{config.tool_id}",
                    "type": config.tool_type
                }
    
    async def _execute_adapter_viser(
        self,
        config: Any,
        parameters: Dict,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """
        执行 adapter-viser（视觉控制）
        用户感知：在工作区看到操作过程
        """
        try:
            from backend.vis.hybrid_executor import hee
            
            # adapter-viser 执行会生成截图、鼠标轨迹等
            # 这些通过 WebSocket 推送给前端显示
            result = await hee.execute(
                task_id=task_id,
                step={
                    "direction": parameters.get("action", "visual_operation"),
                    "tool": f"adapter-viser:{config.tool_id}",
                    "validation": parameters.get("validation", "")
                }
            )
            
            return {
                "success": result.success,
                "result": result.data,
                "type": "adapter-viser"
            }
        except ImportError:
            return {
                "success": True,
                "result": f"[MOCK] adapter-viser executed: {config.tool_id}",
                "type": "adapter-viser"
            }
    
    async def _execute_blueprint(
        self,
        adapter: Adapter,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """执行 Blueprint Adapter（工作流编排）"""
        config = adapter.blueprint_config
        
        if not config:
            return {"success": False, "error": "No blueprint_config found"}
        
        step_results = []
        
        if config.execution_mode == "sequential":
            # 串行执行
            for step in config.steps:
                if not self._running_tasks.get(task_id, True):
                    break  # 任务被暂停
                
                step_result = await self._execute_blueprint_step(step, context, task_id)
                step_results.append(step_result)
                
                if not step_result.get("success"):
                    break  # 失败停止
                    
        elif config.execution_mode == "parallel":
            # 并行执行
            step_tasks = [
                self._execute_blueprint_step(step, context, task_id)
                for step in config.steps
            ]
            step_results = await asyncio.gather(*step_tasks)
        
        # 检查整体成功
        all_success = all(r.get("success") for r in step_results)
        
        return {
            "success": all_success,
            "step_results": step_results,
            "execution_mode": config.execution_mode
        }
    
    async def _execute_blueprint_step(
        self,
        step: BlueprintStep,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """执行 Blueprint 中的一个步骤"""
        step.status = "running"
        step.started_at = time.time()
        
        attached_results = []
        
        # 执行步骤绑定的所有 Adapter
        for attachment in step.attached_adapters:
            adapter_result = await self.execute(
                attachment.adapter_ref,
                {**context, "parent_step": step.id},
                task_id
            )
            attached_results.append({
                "adapter_id": attachment.adapter_id,
                "result": adapter_result
            })
        
        step.status = "completed" if all(
            r["result"].get("success") for r in attached_results
        ) else "failed"
        step.completed_at = time.time()
        
        return {
            "step_id": step.id,
            "success": step.status == "completed",
            "adapter_results": attached_results
        }
    
    async def _execute_agent(
        self,
        adapter: Adapter,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """执行 Agent 编排 Adapter"""
        config = adapter.agent_config
        
        if not config:
            return {"success": False, "error": "No agent_config found"}
        
        if config.collaboration_mode == "sequence":
            return await self._execute_agents_sequential(config, context, task_id)
        elif config.collaboration_mode == "parallel":
            return await self._execute_agents_parallel(config, context, task_id)
        elif config.collaboration_mode == "debate":
            return await self._execute_agents_debate(config, context, task_id)
        else:
            return await self._execute_agents_hierarchy(config, context, task_id)
    
    async def _execute_agents_sequential(
        self,
        config: Any,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """串行执行 Agents（接力模式）"""
        results = []
        shared = dict(config.shared_context)
        
        for agent in config.agents:
            agent_context = {
                **context,
                "shared": shared,
                "agent_role": agent.role
            }
            
            result = await self._execute_single_agent(agent, agent_context, task_id)
            results.append({"agent": agent.agent_id, "result": result})
            
            # 更新共享上下文
            if result.get("success"):
                shared[f"{agent.agent_id}_output"] = result.get("result")
        
        return {
            "success": all(r["result"].get("success") for r in results),
            "results": results,
            "shared_context": shared
        }
    
    async def _execute_agents_parallel(
        self,
        config: Any,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """并行执行 Agents"""
        tasks = []
        for agent in config.agents:
            agent_context = {
                **context,
                "shared": config.shared_context,
                "agent_role": agent.role
            }
            tasks.append(self._execute_single_agent(agent, agent_context, task_id))
        
        results = await asyncio.gather(*tasks)
        
        return {
            "success": all(r.get("success") for r in results),
            "results": [{"agent": a.agent_id, "result": r} 
                       for a, r in zip(config.agents, results)]
        }
    
    async def _execute_agents_debate(
        self,
        config: Any,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """辩论模式执行 Agents"""
        # 简化实现：收集所有 Agent 的观点
        results = await self._execute_agents_parallel(config, context, task_id)
        
        # 合并结果作为"共识"
        consensus = {
            "debate_results": results["results"],
            "consensus": "Agreement reached" if results["success"] else "Disagreement"
        }
        
        return {
            "success": results["success"],
            "result": consensus,
            "mode": "debate"
        }
    
    async def _execute_agents_hierarchy(
        self,
        config: Any,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """层级执行 Agents"""
        # 按优先级排序
        sorted_agents = sorted(config.agents, key=lambda a: a.priority)
        
        # 高优先级先执行
        if sorted_agents:
            primary = sorted_agents[0]
            result = await self._execute_single_agent(primary, context, task_id)
            
            # 如果成功，其他 Agent 审核
            if result.get("success") and len(sorted_agents) > 1:
                review_context = {**context, "primary_result": result}
                reviews = await asyncio.gather(*[
                    self._execute_single_agent(a, review_context, task_id)
                    for a in sorted_agents[1:]
                ])
                
                return {
                    "success": all(r.get("success") for r in reviews),
                    "primary_result": result,
                    "reviews": [{"agent": a.agent_id, "result": r} 
                               for a, r in zip(sorted_agents[1:], reviews)]
                }
            
            return {"success": result.get("success"), "result": result}
        
        return {"success": False, "error": "No agents in hierarchy"}
    
    async def _execute_single_agent(
        self,
        agent: Any,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """执行单个 Agent"""
        # Agent 使用其 capability 中的第一个 Adapter
        if agent.adapter_capabilities:
            adapter_id = agent.adapter_capabilities[0]
            adapter = adapter_registry.get(adapter_id)
            if adapter:
                return await self.execute(adapter, context, task_id)
        
        return {"success": False, "error": f"Agent {agent.agent_id} has no adapter"}
    
    async def _execute_reference(
        self,
        adapter: Adapter,
        context: Dict,
        task_id: str
    ) -> Dict[str, Any]:
        """执行引用 Adapter"""
        ref_adapter = adapter_registry.get(adapter.reference_to)
        if not ref_adapter:
            return {
                "success": False,
                "error": f"Referenced adapter not found: {adapter.reference_to}"
            }
        
        return await self.execute(ref_adapter, context, task_id)
    
    async def _push_status(
        self,
        task_id: str,
        adapter_id: str,
        status: str,
        result: Optional[Dict] = None
    ):
        """推送执行状态到前端"""
        try:
            from backend.websocket.message_router import broadcast_to_task
            
            message = {
                "type": "adapter.execution_status",
                "payload": {
                    "adapter_id": adapter_id,
                    "status": status,
                    "result": result
                },
                "task_id": task_id
            }
            
            await broadcast_to_task(task_id, message)
        except ImportError:
            pass  # WebSocket 不可用
    
    def _map_inputs_to_parameters(
        self,
        parameters: Dict,
        input_mapping: Dict,
        processed_inputs: Dict
    ) -> Dict:
        """将多模态输入映射到工具参数"""
        mapped = dict(parameters)
        
        for param_key, input_ref in input_mapping.items():
            # 支持格式："images[0]", "texts[0]", "tools[0].result"
            try:
                if input_ref.startswith("images["):
                    idx = int(input_ref[7:-1])
                    mapped[param_key] = processed_inputs["images"][idx]["data"]
                elif input_ref.startswith("texts["):
                    idx = int(input_ref[6:-1])
                    mapped[param_key] = processed_inputs["texts"][idx]
                elif input_ref.startswith("tools["):
                    idx = int(input_ref[6:input_ref.find("]")])
                    if ".result" in input_ref:
                        mapped[param_key] = processed_inputs["tools"][idx]["result"]
                elif input_ref == "combined":
                    mapped[param_key] = processed_inputs["combined"]
            except (IndexError, KeyError):
                pass  # 保留原参数值
        
        return mapped
    
    async def _execute_tool_input(
        self,
        inp: MultimodalInput,
        context: Dict,
        task_id: str
    ) -> Dict:
        """执行工具类型的输入"""
        try:
            from backend.tools.registry import tool_registry
            return await tool_registry.execute_tool(
                tool_id=inp.ref_id,
                context={"task_id": task_id, **context},
                parameters={}
            )
        except ImportError:
            return {"success": True, "result": f"[MOCK] Tool input: {inp.ref_id}"}
    
    def _get_adapter_input(self, adapter_id: str) -> Optional[Adapter]:
        """获取 Adapter 类型的输入"""
        return adapter_registry.get(adapter_id)
    
    def pause(self, task_id: str):
        """暂停任务"""
        self._running_tasks[task_id] = False
    
    def resume(self, task_id: str):
        """恢复任务"""
        self._running_tasks[task_id] = True


# 全局实例
adapter_execution_engine = AdapterExecutionEngine()
