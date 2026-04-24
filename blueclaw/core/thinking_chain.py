# -*- coding: utf-8 -*-
"""
thinking_chain.py - 可追问的思考链管理

职责: 管理多轮澄清的思考节点链
支持:
- 创建澄清节点
- 记录用户选择
- 判断收敛条件
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid


class NodeStatus(Enum):
    """思考节点状态"""
    ACTIVE = "active"       # 活跃，等待用户选择
    RESOLVED = "resolved"   # 已解决
    SKIPPED = "skipped"     # 被跳过


@dataclass
class ThinkingNode:
    """思考节点"""
    node_id: str
    question: str  # 当前节点的问题
    options: List[Dict[str, Any]]  # 选项列表
    user_choice: Optional[str] = None  # 用户选择
    custom_input: Optional[str] = None  # 用户自定义输入
    parent_node_id: Optional[str] = None
    child_node_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    status: NodeStatus = field(default=NodeStatus.ACTIVE)
    node_type: str = field(default="clarification")  # 节点类型
    
    # 附加信息
    intent_type: Optional[str] = field(default=None)
    confidence: float = field(default=0.5)
    extracted_info: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def content(self) -> str:
        """获取节点内容（兼容接口）"""
        return self.question if self.question else ""


class ThinkingChain:
    """思考节点链管理器"""
    
    def __init__(self, session_id: str):
        """
        初始化思考链
        
        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self.nodes: Dict[str, ThinkingNode] = {}
        self.root_node_id: Optional[str] = None
        self.current_node_id: Optional[str] = None
        self.converged: bool = False
        self.final_intent: Optional[Dict[str, Any]] = None
    
    def create_root_node(self, question: str, options: List[Dict[str, Any]]) -> ThinkingNode:
        """
        创建根节点
        
        Args:
            question: 初始问题
            options: 选项列表
            
        Returns:
            ThinkingNode: 创建的根节点
        """
        node_id = f"root_{uuid.uuid4().hex[:8]}"
        node = ThinkingNode(
            node_id=node_id,
            question=question,
            options=options,
            parent_node_id=None
        )
        
        self.nodes[node_id] = node
        self.root_node_id = node_id
        self.current_node_id = node_id
        
        return node
    
    def add_clarification_node(
        self,
        parent_node_id: str,
        question: str,
        options: List[Dict[str, Any]],
        intent_type: Optional[str] = None,
        confidence: float = 0.5
    ) -> ThinkingNode:
        """
        添加澄清节点
        
        Args:
            parent_node_id: 父节点ID
            question: 澄清问题
            options: 选项列表
            intent_type: 意图类型
            confidence: 置信度
            
        Returns:
            ThinkingNode: 创建的节点
        """
        node_id = f"clarify_{uuid.uuid4().hex[:8]}"
        
        node = ThinkingNode(
            node_id=node_id,
            question=question,
            options=options,
            parent_node_id=parent_node_id,
            intent_type=intent_type,
            confidence=confidence
        )
        
        self.nodes[node_id] = node
        
        # 更新父节点的子节点列表
        parent = self.nodes.get(parent_node_id)
        if parent:
            parent.child_node_ids.append(node_id)
        
        self.current_node_id = node_id
        
        return node
    
    def resolve_node(self, node_id: str, choice: str, 
                    custom_input: Optional[str] = None) -> bool:
        """
        解决节点（用户做出选择）
        
        Args:
            node_id: 节点ID
            choice: 用户选择的选项ID
            custom_input: 用户自定义输入
            
        Returns:
            bool: 是否成功
        """
        node = self.nodes.get(node_id)
        if not node:
            return False
        
        node.user_choice = choice
        node.custom_input = custom_input
        node.status = NodeStatus.RESOLVED
        node.resolved_at = datetime.now()
        
        # 检查是否收敛
        self._check_convergence()
        
        return True
    
    def skip_node(self, node_id: str) -> bool:
        """跳过节点"""
        node = self.nodes.get(node_id)
        if not node:
            return False
        
        node.status = NodeStatus.SKIPPED
        return True
    
    def get_node_path(self, node_id: str) -> List[ThinkingNode]:
        """
        获取从根节点到指定节点的路径
        
        Args:
            node_id: 目标节点ID
            
        Returns:
            List[ThinkingNode]: 节点路径
        """
        path = []
        current_id = node_id
        
        while current_id:
            node = self.nodes.get(current_id)
            if node:
                path.append(node)
                current_id = node.parent_node_id
            else:
                break
        
        return list(reversed(path))
    
    def get_resolved_path(self) -> List[ThinkingNode]:
        """获取已解决的路径（从根到当前）"""
        if not self.current_node_id:
            return []
        
        path = self.get_node_path(self.current_node_id)
        return [n for n in path if n.status == NodeStatus.RESOLVED]
    
    def _check_convergence(self):
        """检查是否收敛（信息足够）"""
        # 简化逻辑：如果有任意节点被解决，认为可能收敛
        resolved_count = sum(1 for n in self.nodes.values() 
                           if n.status == NodeStatus.RESOLVED)
        
        # 至少解决一个节点，且当前节点已解决
        if resolved_count >= 1 and self.current_node_id:
            current = self.nodes.get(self.current_node_id)
            if current and current.status == NodeStatus.RESOLVED:
                # 可以在这里添加更复杂的收敛判断
                pass
    
    def mark_converged(self, final_intent: Dict[str, Any]):
        """标记为已收敛"""
        self.converged = True
        self.final_intent = final_intent
    
    def is_converged(self) -> bool:
        """检查是否已收敛"""
        return self.converged
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "root_node_id": self.root_node_id,
            "current_node_id": self.current_node_id,
            "converged": self.converged,
            "final_intent": self.final_intent,
            "nodes": {
                nid: {
                    "node_id": n.node_id,
                    "question": n.question,
                    "options": n.options,
                    "user_choice": n.user_choice,
                    "status": n.status.value,
                    "parent_node_id": n.parent_node_id,
                    "child_node_ids": n.child_node_ids
                }
                for nid, n in self.nodes.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThinkingChain':
        """从字典反序列化"""
        chain = cls(data["session_id"])
        chain.root_node_id = data.get("root_node_id")
        chain.current_node_id = data.get("current_node_id")
        chain.converged = data.get("converged", False)
        chain.final_intent = data.get("final_intent")
        
        for nid, ndata in data.get("nodes", {}).items():
            node = ThinkingNode(
                node_id=ndata["node_id"],
                question=ndata["question"],
                options=ndata["options"],
                user_choice=ndata.get("user_choice"),
                parent_node_id=ndata.get("parent_node_id")
            )
            node.status = NodeStatus(ndata.get("status", "active"))
            node.child_node_ids = ndata.get("child_node_ids", [])
            chain.nodes[nid] = node
        
        return chain
