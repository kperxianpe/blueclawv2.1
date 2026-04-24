#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thinking Engine - Complete implementation

Handles clarification flow with:
- Option generation (A/B/C)
- Custom input support
- Thinking chain management
- Position tracking for visualization
"""

import json
import asyncio
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class NodeStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    SKIPPED = "skipped"


@dataclass
class ThinkingOption:
    id: str
    label: str
    description: str
    confidence: float
    recommended: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "confidence": self.confidence,
            "recommended": self.recommended
        }


@dataclass
class ThinkingNode:
    """思考节点 - 支持可视化位置"""
    id: str
    question: str
    options: List[ThinkingOption]
    allow_custom: bool = True
    parent_id: Optional[str] = None
    selected_option_id: Optional[str] = None
    custom_input: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    position: Dict[str, int] = field(default_factory=dict)
    status: NodeStatus = field(default=NodeStatus.ACTIVE)
    
    def __post_init__(self):
        if not self.position:
            self.position = {"x": 100, "y": 200}
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "options": [opt.to_dict() for opt in self.options],
            "allow_custom": self.allow_custom,
            "parent_id": self.parent_id,
            "selected_option_id": self.selected_option_id,
            "custom_input": self.custom_input,
            "created_at": self.created_at,
            "position": self.position,
            "status": self.status.value
        }


class ThinkingEngine:
    """思考引擎 - 管理澄清流程"""
    
    AUTO_SELECT_THRESHOLD = 0.85
    MAX_DEPTH = 3
    
    def __init__(self):
        self.nodes: Dict[str, ThinkingNode] = {}
        self.task_nodes: Dict[str, List[str]] = {}
    
    async def generate_initial_node(self, task_id: str, user_input: str, node_index: int = 0) -> ThinkingNode:
        """生成初始思考节点"""
        from blueclaw.llm import LLMClient, Message
        from blueclaw.llm.prompts import format_thinking_options_prompt
        
        prompt = format_thinking_options_prompt(context=user_input, history=[])
        
        try:
            response = await LLMClient().chat_completion(
                [
                    Message(role="system", content="You are a decision assistant. Output valid JSON only."),
                    Message(role="user", content=prompt)
                ]
            )
            
            # 提取 JSON（处理 Markdown 代码块）
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
        except Exception as e:
            print(f"LLM error, using defaults: {e}")
            result = self._create_default_options(user_input)
        
        node = ThinkingNode(
            id=f"thinking_{uuid.uuid4().hex[:8]}",
            question=result.get("question", "请选择下一步:"),
            options=[
                ThinkingOption(
                    id=opt.get("id", chr(65 + i)),
                    label=opt.get("label", f"选项{i+1}"),
                    description=opt.get("description", ""),
                    confidence=opt.get("confidence", 0.5),
                    recommended=opt.get("recommended", i == 0)
                ) for i, opt in enumerate(result.get("options", []))
            ],
            allow_custom=True,
            position={"x": 100 + node_index * 300, "y": 200}
        )
        
        self.nodes[node.id] = node
        if task_id not in self.task_nodes:
            self.task_nodes[task_id] = []
        self.task_nodes[task_id].append(node.id)
        
        return node
    
    async def select_option_impl(
        self,
        task_id: str,
        node_id: str,
        option_id: str,
        custom_input: Optional[str] = None
    ) -> Optional[ThinkingNode]:
        """
        处理用户选择（内部实现）
        - option_id: A/B/C 选项
        - custom_input: 自定义输入（第4个白块）
        """
        current_node = self.nodes.get(node_id)
        if not current_node:
            print(f"[DEBUG select_option_impl] node not found: {node_id}")
            return None
        
        current_node.selected_option_id = option_id
        current_node.custom_input = custom_input
        current_node.status = NodeStatus.RESOLVED
        
        # 获取选中的选项内容
        selected_option = None
        for opt in current_node.options:
            if opt.id == option_id:
                selected_option = opt
                break
        
        # 使用自定义输入
        if custom_input:
            selected_option = ThinkingOption(
                id="custom",
                label="自定义",
                description=custom_input,
                confidence=1.0,
                recommended=True
            )
        
        if not selected_option:
            print(f"[DEBUG select_option_impl] selected_option not found for {option_id}")
            return None
        
        # 判断是否收敛（思考3层后收敛）
        current_path = self._get_thinking_path(task_id, node_id)
        print(f"[DEBUG select_option_impl] task={task_id}, node={node_id}, path_len={len(current_path)}, MAX_DEPTH={self.MAX_DEPTH}")
        if len(current_path) >= self.MAX_DEPTH:
            print(f"[DEBUG select_option_impl] CONVERGED: path_len={len(current_path)} >= MAX_DEPTH={self.MAX_DEPTH}")
            return None  # 思考收敛
        
        # 生成下一个节点
        next_node_index = len(self.task_nodes.get(task_id, []))
        next_node = await self._generate_next_node(
            task_id=task_id,
            parent_id=node_id,
            context=self._build_context_from_path(current_path + [selected_option]),
            node_index=next_node_index
        )
        
        # 检查是否应自动选择（AI 高置信度推荐）
        if next_node:
            auto_option_id = self.should_auto_select(next_node)
            if auto_option_id:
                print(f"[ThinkingEngine] Auto-selecting option {auto_option_id} for node {next_node.id} (confidence >= {self.AUTO_SELECT_THRESHOLD})")
                return await self.select_option_impl(task_id, next_node.id, auto_option_id)
        
        return next_node
    
    async def _generate_next_node(self, task_id: str, parent_id: str, context: str, node_index: int) -> ThinkingNode:
        """生成下一个思考节点"""
        from blueclaw.llm import LLMClient, Message
        from blueclaw.llm.prompts import format_thinking_options_prompt
        
        prompt = format_thinking_options_prompt(context=context, history=[])
        
        try:
            response = await LLMClient().chat_completion(
                [
                    Message(role="system", content="You are a decision assistant. Output valid JSON only."),
                    Message(role="user", content=prompt)
                ]
            )
            
            result = json.loads(response.content)
        except Exception as e:
            print(f"LLM error, using defaults: {e}")
            result = self._create_default_options(context)
        
        node = ThinkingNode(
            id=f"thinking_{uuid.uuid4().hex[:8]}",
            question=result.get("question", "请继续选择:"),
            options=[
                ThinkingOption(
                    id=opt.get("id", chr(65 + i)),
                    label=opt.get("label", f"选项{i+1}"),
                    description=opt.get("description", ""),
                    confidence=opt.get("confidence", 0.5),
                    recommended=opt.get("recommended", i == 0)
                ) for i, opt in enumerate(result.get("options", []))
            ],
            allow_custom=True,
            parent_id=parent_id,
            position={"x": 100 + node_index * 300, "y": 200}
        )
        
        self.nodes[node.id] = node
        if task_id not in self.task_nodes:
            print(f"[WARNING] _generate_next_node: task_id {task_id} not in task_nodes, initializing")
            self.task_nodes[task_id] = []
        self.task_nodes[task_id].append(node.id)
        
        return node
    
    def get_thinking_path(self, task_id: str) -> List[ThinkingNode]:
        """获取任务完整思考路径"""
        node_ids = self.task_nodes.get(task_id, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]
    
    def _get_thinking_path(self, task_id: str, up_to_node_id: str) -> List[ThinkingOption]:
        """获取到指定节点的思考路径"""
        path = []
        current_id = up_to_node_id
        
        while current_id:
            node = self.nodes.get(current_id)
            if not node:
                break
            
            if node.selected_option_id:
                for opt in node.options:
                    if opt.id == node.selected_option_id:
                        path.insert(0, opt)
                        break
            
            current_id = node.parent_id
        
        return path
    
    def _build_context_from_path(self, path: List[ThinkingOption]) -> str:
        return " - ".join([opt.label for opt in path])
    
    def _create_default_options(self, context: str) -> dict:
        return {
            "question": f"关于'{context}'，请选择:",
            "options": [
                {"id": "A", "label": "自动处理", "description": "AI自动完成最佳方案", "confidence": 0.8, "recommended": True},
                {"id": "B", "label": "详细规划", "description": "逐步确认每个步骤", "confidence": 0.6},
                {"id": "C", "label": "简单处理", "description": "快速完成基础需求", "confidence": 0.5}
            ]
        }


    async def start_thinking(self, task_id: str, user_input: str) -> ThinkingNode:
        """开始思考 - 生成初始节点"""
        return await self.generate_initial_node(task_id, user_input, node_index=0)
    
    async def restart_thinking_from_intervention(
        self,
        task_id: str,
        original_input: str,
        completed_summary: str,
        intervention_input: str
    ) -> ThinkingNode:
        """从干预上下文重新启动思考流程"""
        # 清除该任务旧的思考节点记录，开始全新思考链
        self.task_nodes[task_id] = []
        
        context = (
            f"原始任务: {original_input}\n"
            f"已完成的执行步骤: {completed_summary}\n"
            f"用户希望调整: {intervention_input}\n"
            f"请基于以上上下文，重新思考下一步的最佳方案。"
        )
        
        return await self.generate_initial_node(task_id, context, node_index=0)
    
    def should_auto_select(self, node: ThinkingNode) -> Optional[str]:
        """检查是否有高置信度选项可自动选择"""
        for opt in node.options:
            if opt.confidence >= self.AUTO_SELECT_THRESHOLD:
                return opt.id
        return None
    
    def is_converged(self, task_id: str) -> bool:
        """检查任务是否已收敛"""
        node_ids = self.task_nodes.get(task_id, [])
        if not node_ids:
            return False
        last_node = self.nodes.get(node_ids[-1])
        if not last_node:
            return False
        # 最后一个节点已选择，或无可选选项
        return last_node.selected_option_id is not None or not last_node.options
    
    async def converge(self, task_id: str) -> Optional[List[dict]]:
        """强制收敛思考流程，返回最终路径"""
        if not self.is_converged(task_id):
            return None
        return self._get_thinking_path_as_dicts(task_id)
    
    async def select_option(
        self,
        task_id: str,
        node_id: str,
        option_id: str
    ) -> dict:
        """选择选项 - 返回结果字典"""
        next_node = await self.select_option_impl(task_id, node_id, option_id)
        
        if next_node is None:
            # 思考收敛
            final_path = self._get_thinking_path_as_dicts(task_id)
            return {
                "has_more_options": False,
                "final_path": final_path,
                "converged": True
            }
        
        return {
            "has_more_options": True,
            "next_node": next_node,
            "converged": False
        }
    
    async def select_custom_input(
        self,
        task_id: str,
        node_id: str,
        custom_input: str
    ) -> dict:
        """自定义输入（第4个白块）"""
        next_node = await self.select_option_impl(task_id, node_id, "custom", custom_input)
        
        if next_node is None:
            final_path = self._get_thinking_path_as_dicts(task_id)
            return {
                "has_more_options": False,
                "final_path": final_path,
                "converged": True
            }
        
        return {
            "has_more_options": True,
            "next_node": next_node,
            "converged": False
        }
    
    def get_final_path(self, task_id: str) -> List[dict]:
        """获取最终思考路径"""
        return self._get_thinking_path_as_dicts(task_id)
    
    def _get_thinking_path_as_dicts(self, task_id: str) -> List[dict]:
        """获取思考路径作为字典列表"""
        node_ids = self.task_nodes.get(task_id, [])
        path = []
        for nid in node_ids:
            node = self.nodes.get(nid)
            if node:
                selected = None
                if node.selected_option_id:
                    for opt in node.options:
                        if opt.id == node.selected_option_id:
                            selected = opt
                            break
                
                path.append({
                    "node_id": node.id,
                    "question": node.question,
                    "selected_option": selected.to_dict() if selected else None,
                    "custom_input": node.custom_input
                })
        return path


# Global instance
thinking_engine = ThinkingEngine()
