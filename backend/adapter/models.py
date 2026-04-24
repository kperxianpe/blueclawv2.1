#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter 数据模型
V2 核心：AI工具的工具，递归可组合的元工具
"""
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field
from copy import deepcopy
from enum import Enum
import uuid
import time


class AdapterType(Enum):
    """Adapter 类型"""
    SINGLE = "single"       # 单工具封装
    BLUEPRINT = "blueprint" # 嵌套工作流编排
    AGENT = "agent"         # Agent 协作编排
    REFERENCE = "reference" # 引用其他 Adapter


class AdapterLevel(Enum):
    """Adapter 层级"""
    ATOMIC = 0      # 原子层（不可再分）
    COMPOSITE = 1   # 组合层（可包含其他 Adapter）
    ORCHESTRA = 2   # 编排层（多 Agent）


@dataclass
class MultimodalInput:
    """
    多模态输入项
    支持传统模态 + 工具模态 + 元模态
    """
    type: Literal[
        "image", "video", "audio", "file", "text",  # 传统模态
        "tool", "skill", "adapter"                   # 扩展模态
    ]
    source: str  # URL / base64 / file_path / 引用ID
    mime_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    thumbnail: Optional[str] = None  # 预览图 base64
    
    # 工具/Adapter 类型特有的引用信息
    ref_id: Optional[str] = None  # 引用的 tool_id / adapter_id
    ref_type: Optional[str] = None  # "mcp" / "skill" / "adapter"


@dataclass
class SingleConfig:
    """单工具封装配置"""
    tool_type: Literal["mcp", "skill", "adapter-viser"]
    tool_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 多模态输入到参数的映射
    # 例如：{"image": "inputs[0]", "query": "inputs[1].source"}
    input_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class BlueprintStep:
    """工作流中的步骤"""
    id: str
    name: str
    description: str
    
    # 可绑定多个 Adapter（右上角显示）
    attached_adapters: List["AdapterAttachment"] = field(default_factory=list)
    
    # 执行状态
    status: Literal["pending", "running", "completed", "failed", "paused"] = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "attached_adapters_count": len(self.attached_adapters),
            "status": self.status
        }


@dataclass
class BlueprintConfig:
    """工作流编排配置"""
    steps: List[BlueprintStep]
    execution_mode: Literal["sequential", "parallel", "conditional"] = "sequential"
    
    # 数据流定义（步骤间数据传递）
    data_flow: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "execution_mode": self.execution_mode,
            "step_count": len(self.steps)
        }


@dataclass
class AdapterAttachment:
    """步骤与 Adapter 的绑定关系"""
    adapter_id: str
    adapter_ref: "Adapter"  # 深拷贝快照
    position: Literal["top-right", "embedded"] = "top-right"
    locked: bool = False  # 锁定后强制使用此 Adapter
    execution_order: int = 0  # 多 Adapter 时的执行顺序
    execution_mode: Literal["auto", "manual"] = "auto"  # 自动/手动触发


@dataclass
class AgentRef:
    """Agent 引用定义"""
    agent_id: str
    name: str
    role: str  # researcher / writer / reviewer / executor / planner
    adapter_capabilities: List[str]  # 该 Agent 可使用的 Adapter 类型
    priority: int = 1
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Agent 协作编排配置"""
    agents: List[AgentRef]
    collaboration_mode: Literal["sequence", "parallel", "hierarchy", "debate"]
    
    # 路由策略：如何分配任务给 Agents
    routing_strategy: Literal["static", "llm", "rule-based"] = "llm"
    
    # 共享上下文
    shared_context: Dict[str, Any] = field(default_factory=dict)
    
    # 共识机制（debate 模式使用）
    consensus_config: Optional[Dict[str, Any]] = None


@dataclass
class Adapter:
    """
    Adapter - AI工具的工具
    V2 核心：递归可组合的元工具维度
    """
    # 基础信息
    id: str
    name: str
    description: str
    icon: str  # emoji
    color: str  # hex color
    
    # 类型与层级
    adapter_type: AdapterType
    level: AdapterLevel = AdapterLevel.ATOMIC
    
    # 核：执行逻辑（根据 adapter_type 选择）
    single_config: Optional[SingleConfig] = None
    blueprint_config: Optional[BlueprintConfig] = None
    agent_config: Optional[AgentConfig] = None
    reference_to: Optional[str] = None  # type=REFERENCE 时使用
    
    # 多模态输入（Adapter 的上下文）
    inputs: List[MultimodalInput] = field(default_factory=list)
    
    # 递归：子 Adapter 列表（用于嵌套）
    children: List["Adapter"] = field(default_factory=list)
    
    # 元数据
    created_by: str = "user"  # user / system / agent
    is_template: bool = False  # 是否显示在左侧面板
    tags: List[str] = field(default_factory=list)
    
    # 版本控制
    version: str = "1.0.0"
    parent_id: Optional[str] = None  # 克隆/引用来源
    created_at: float = field(default_factory=lambda: time.time())
    
    def to_dict(self) -> dict:
        """序列化为前端可用格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "type": self.adapter_type.value,
            "level": self.level.value,
            "inputs": [
                {
                    "type": inp.type,
                    "mime_type": inp.mime_type,
                    "has_thumbnail": inp.thumbnail is not None,
                    "is_tool": inp.type in ["tool", "skill"],
                    "is_adapter": inp.type == "adapter"
                }
                for inp in self.inputs
            ],
            "input_count": len(self.inputs),
            "has_children": len(self.children) > 0,
            "children_count": len(self.children),
            "is_template": self.is_template,
            "created_by": self.created_by,
            "blueprint": self.blueprint_config.to_dict() if self.blueprint_config else None
        }


class AdapterRegistry:
    """
    Adapter 注册表
    管理所有 Adapter，支持模板、克隆、嵌套查询
    """
    
    def __init__(self):
        self._adapters: Dict[str, Adapter] = {}
        self._templates: List[str] = []  # 模板 ID 列表
        
        # 初始化默认模板
        self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认模板"""
        default_templates = [
            Adapter(
                id="template_web_search",
                name="Web Search",
                description="Search the web for information",
                icon="🌐",
                color="#F59E0B",
                adapter_type=AdapterType.SINGLE,
                level=AdapterLevel.ATOMIC,
                single_config=SingleConfig(tool_type="mcp", tool_id="web_search"),
                is_template=True,
                created_by="system"
            ),
            Adapter(
                id="template_image_gen",
                name="Image Gen",
                description="Generate images from text",
                icon="🎨",
                color="#FBBF24",
                adapter_type=AdapterType.SINGLE,
                level=AdapterLevel.ATOMIC,
                single_config=SingleConfig(tool_type="skill", tool_id="image_gen"),
                is_template=True,
                created_by="system"
            ),
            Adapter(
                id="template_code_runner",
                name="Code Runner",
                description="Execute code snippets safely",
                icon="💻",
                color="#10B981",
                adapter_type=AdapterType.SINGLE,
                level=AdapterLevel.ATOMIC,
                single_config=SingleConfig(tool_type="skill", tool_id="code_runner"),
                is_template=True,
                created_by="system"
            ),
        ]
        for tmpl in default_templates:
            self._adapters[tmpl.id] = tmpl
            self._templates.append(tmpl.id)
    
    def create(self, adapter: Adapter) -> Adapter:
        """创建新的 Adapter"""
        if not adapter.id:
            adapter.id = f"adapter_{uuid.uuid4().hex[:12]}"
        
        # 自动计算层级
        adapter.level = self._calculate_level(adapter)
        
        # 深拷贝存储
        self._adapters[adapter.id] = deepcopy(adapter)
        
        return deepcopy(adapter)
    
    def get(self, adapter_id: str) -> Optional[Adapter]:
        """获取 Adapter（返回深拷贝）"""
        adapter = self._adapters.get(adapter_id)
        return deepcopy(adapter) if adapter else None
    
    def get_snapshot(self, adapter_id: str) -> Optional[Adapter]:
        """
        获取 Adapter 快照（用于绑定到步骤）
        快照记录 parent_id，原 Adapter 修改不影响已绑定实例
        """
        adapter = self.get(adapter_id)
        if adapter:
            adapter.parent_id = adapter_id
        return adapter
    
    def update(self, adapter_id: str, updates: Dict[str, Any]) -> Optional[Adapter]:
        """更新 Adapter"""
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            return None
        
        for key, value in updates.items():
            if hasattr(adapter, key):
                setattr(adapter, key, value)
        
        # 重新计算层级
        adapter.level = self._calculate_level(adapter)
        return deepcopy(adapter)
    
    def delete(self, adapter_id: str) -> bool:
        """
        删除 Adapter
        检查是否有其他 Adapter 引用它
        """
        # 检查引用
        for adapter in self._adapters.values():
            if adapter.adapter_type == AdapterType.REFERENCE and adapter.reference_to == adapter_id:
                return False  # 被引用，不能删除
            # 检查嵌套引用
            if any(child.id == adapter_id for child in adapter.children):
                return False
        
        if adapter_id in self._adapters:
            del self._adapters[adapter_id]
            if adapter_id in self._templates:
                self._templates.remove(adapter_id)
            return True
        return False
    
    def list_all(self, filter_type: Optional[AdapterType] = None) -> List[Adapter]:
        """列出所有 Adapter"""
        result = list(self._adapters.values())
        if filter_type:
            result = [a for a in result if a.adapter_type == filter_type]
        return [deepcopy(a) for a in result]
    
    def list_templates(self) -> List[Adapter]:
        """获取模板列表（显示在左侧面板）"""
        return [deepcopy(self._adapters[tid]) for tid in self._templates if tid in self._adapters]
    
    def add_template(self, adapter_id: str) -> bool:
        """将 Adapter 添加为模板"""
        if adapter_id in self._adapters and adapter_id not in self._templates:
            self._templates.append(adapter_id)
            self._adapters[adapter_id].is_template = True
            return True
        return False
    
    def clone(self, adapter_id: str, new_name: Optional[str] = None) -> Adapter:
        """克隆 Adapter（深拷贝）"""
        adapter = self.get(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_id}")
        
        adapter.id = f"adapter_{uuid.uuid4().hex[:12]}"
        adapter.name = new_name or f"{adapter.name} (Copy)"
        adapter.parent_id = adapter_id
        adapter.created_at = time.time()
        
        return self.create(adapter)
    
    def wrap_blueprint(self, blueprint_id: str, name: str) -> Adapter:
        """将现有蓝图封装为 Adapter"""
        adapter = Adapter(
            id=f"adapter_bp_{blueprint_id}",
            name=name,
            description=f"Blueprint Adapter: {name}",
            icon="📦",
            color="#FCD34D",
            adapter_type=AdapterType.BLUEPRINT,
            level=AdapterLevel.COMPOSITE,
            blueprint_config=BlueprintConfig(
                steps=[],
                execution_mode="sequential"
            ),
            is_template=False
        )
        return self.create(adapter)
    
    def _calculate_level(self, adapter: Adapter) -> AdapterLevel:
        """计算 Adapter 层级"""
        if adapter.adapter_type == AdapterType.SINGLE:
            return AdapterLevel.ATOMIC
        elif adapter.adapter_type == AdapterType.BLUEPRINT:
            return AdapterLevel.COMPOSITE
        elif adapter.adapter_type == AdapterType.AGENT:
            return AdapterLevel.ORCHESTRA
        elif adapter.adapter_type == AdapterType.REFERENCE:
            # 引用类型继承被引用者的层级
            ref = self._adapters.get(adapter.reference_to)
            return ref.level if ref else AdapterLevel.ATOMIC
        return AdapterLevel.ATOMIC
    
    def get_nesting_depth(self, adapter_id: str, visited: Optional[set] = None) -> int:
        """获取 Adapter 的嵌套深度（用于限制）"""
        if visited is None:
            visited = set()
        
        if adapter_id in visited:
            return float('inf')  # 循环引用
        
        visited.add(adapter_id)
        adapter = self._adapters.get(adapter_id)
        
        if not adapter or not adapter.children:
            return 0
        
        max_child_depth = max(
            self.get_nesting_depth(child.id, visited.copy())
            for child in adapter.children
        )
        return max_child_depth + 1


# 全局注册表
adapter_registry = AdapterRegistry()
