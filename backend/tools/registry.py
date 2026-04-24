#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToolRegistry - 统一工具注册表
Week 20.5 实现：聚合 MCP Tool、Skill、Adapter 为统一的 ToolIcon
"""
from typing import List, Dict, Optional, Literal, Any
from dataclasses import dataclass
from enum import Enum
import asyncio


class ToolType(Enum):
    """工具类型"""
    MCP = "mcp"
    SKILL = "skill"
    ADAPTER = "adapter"
    CODE = "code"


@dataclass
class ToolIcon:
    """工具图标（黄色方块）定义"""
    id: str
    type: ToolType
    name: str
    icon: str  # emoji 或 unicode
    color: str  # hex color
    description: str
    # 可拖拽目标
    droppable_targets: List[Literal["node", "vis-adapter"]]
    # 执行配置
    config: Dict[str, Any]
    # 来源信息
    source: str  # "mcp:filesystem" | "skill:search_web" | "adapter:jianying"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "description": self.description,
            "droppable_targets": self.droppable_targets,
            "config_preview": {
                "parameters": list(self.config.get("parameters", {}).keys())
            },
            "source": self.source
        }


class ToolRegistry:
    """统一工具注册表
    
    整合现有组件：
    - MCPRegistry: 外部 MCP Tools
    - existing_skill_registry: 复用 blueclaw.skills.registry (Week 17)
    - vis.adapters: 现有的视觉适配器
    """
    
    def __init__(self):
        self._icons: Dict[str, ToolIcon] = {}
        self._mcp_registry = None  # 延迟初始化
        self._skill_registry = None  # 延迟初始化
        self._adapters: Dict[str, Any] = {}
    
    def _init_mcp(self):
        """延迟初始化 MCP Registry"""
        if self._mcp_registry is None:
            try:
                from backend.mcp.client import MCPRegistry
                self._mcp_registry = MCPRegistry()
            except ImportError:
                print("[ToolRegistry] MCP SDK not available")
                self._mcp_registry = None
    
    def _init_skills(self):
        """延迟初始化并复用现有的 SkillRegistry"""
        if self._skill_registry is None:
            try:
                from blueclaw.skills.skill_registry import SkillRegistry
                self._skill_registry = SkillRegistry()
            except ImportError:
                try:
                    from blueclaw.skills.registry import SkillRegistry
                    self._skill_registry = SkillRegistry()
                except ImportError:
                    print("[ToolRegistry] SkillRegistry not found")
                    self._skill_registry = None
    
    def _init_adapters(self):
        """延迟初始化并复用现有的 Adapter 实例"""
        if not self._adapters:
            try:
                from backend.vis.adapters import jianying_adapter, blender_adapter
                self._adapters = {
                    "jianying": jianying_adapter,
                    "blender": blender_adapter,
                }
            except ImportError:
                print("[ToolRegistry] Adapters not available")
                self._adapters = {}
    
    async def refresh(self) -> int:
        """
        刷新工具列表，从各来源加载
        返回加载的工具数量
        """
        self._icons.clear()
        
        # 1. 加载 MCP Tools
        await self._load_mcp_tools()
        
        # 2. 加载 Skills
        self._load_skills()
        
        # 3. 加载 Adapters
        self._load_adapters()
        
        return len(self._icons)
    
    async def _load_mcp_tools(self):
        """从 MCP Registry 加载工具"""
        self._init_mcp()
        if self._mcp_registry is None:
            return
        
        try:
            mcp_tools = await self._mcp_registry.discover_tools()
            
            for tool in mcp_tools:
                icon = ToolIcon(
                    id=f"mcp-{tool.server_name}-{tool.name}",
                    type=ToolType.MCP,
                    name=tool.display_name or tool.name,
                    icon="🔌",
                    color="#FCD34D",  # 黄色系
                    description=tool.description or f"MCP Tool: {tool.name}",
                    droppable_targets=["node", "vis-adapter"],
                    config={
                        "server_name": tool.server_name,
                        "tool_name": tool.name,
                        "parameters": tool.parameters_schema,
                    },
                    source=f"mcp:{tool.server_name}"
                )
                self._icons[icon.id] = icon
        except Exception as e:
            print(f"[ToolRegistry] Failed to load MCP tools: {e}")
    
    def _load_skills(self):
        """从现有 SkillRegistry 加载技能"""
        self._init_skills()
        if self._skill_registry is None:
            return
        
        try:
            # 尝试不同的接口
            if hasattr(self._skill_registry, 'get_all_skills'):
                skills = self._skill_registry.get_all_skills()
                for skill_id, skill in skills.items():
                    icon = ToolIcon(
                        id=f"skill-{skill_id}",
                        type=ToolType.SKILL,
                        name=getattr(skill, 'name', skill_id),
                        icon="⚡",
                        color="#FBBF24",
                        description=getattr(skill, 'description', f"Skill: {skill_id}"),
                        droppable_targets=["node", "vis-adapter"],
                        config={
                            "skill_id": skill_id,
                            "version": getattr(skill, 'version', '1.0.0'),
                            "parameters": getattr(skill, 'parameters', {}),
                        },
                        source=f"skill:{skill_id}"
                    )
                    self._icons[icon.id] = icon
            
            elif hasattr(self._skill_registry, 'list_skills'):
                skill_names = self._skill_registry.list_skills()
                for skill_name in skill_names:
                    skill = self._skill_registry.get(skill_name)
                    if skill:
                        icon = ToolIcon(
                            id=f"skill-{skill_name}",
                            type=ToolType.SKILL,
                            name=getattr(skill, 'name', skill_name),
                            icon="⚡",
                            color="#FBBF24",
                            description=getattr(skill, 'description', f"Skill: {skill_name}"),
                            droppable_targets=["node", "vis-adapter"],
                            config={
                                "skill_id": skill_name,
                                "version": getattr(skill, 'version', '1.0.0'),
                                "parameters": getattr(skill, 'parameters', {}),
                            },
                            source=f"skill:{skill_name}"
                        )
                        self._icons[icon.id] = icon
        except Exception as e:
            print(f"[ToolRegistry] Failed to load skills: {e}")
    
    def _load_adapters(self):
        """从现有 Adapter 实例加载适配器"""
        self._init_adapters()
        
        for adapter_type, adapter in self._adapters.items():
            try:
                icon = ToolIcon(
                    id=f"adapter-{adapter_type}",
                    type=ToolType.ADAPTER,
                    name=getattr(adapter, 'app_name', adapter_type.title()),
                    icon="👁️",
                    color="#F59E0B",
                    description=f"视觉控制: {getattr(adapter, 'app_name', adapter_type)}",
                    droppable_targets=["node", "vis-adapter"],
                    config={
                        "adapter_type": adapter_type,
                        "actions": getattr(adapter, 'element_hints', {}).keys() if hasattr(adapter, 'element_hints') else [],
                    },
                    source=f"adapter:{adapter_type}"
                )
                self._icons[icon.id] = icon
            except Exception as e:
                print(f"[ToolRegistry] Failed to load adapter {adapter_type}: {e}")
    
    def list_all(self) -> List[ToolIcon]:
        """获取所有工具图标"""
        return list(self._icons.values())
    
    def get(self, tool_id: str) -> Optional[ToolIcon]:
        """获取指定工具图标"""
        return self._icons.get(tool_id)
    
    def filter_by_type(self, tool_type: ToolType) -> List[ToolIcon]:
        """按类型筛选工具"""
        return [icon for icon in self._icons.values() if icon.type == tool_type]
    
    async def execute_tool(
        self,
        tool_id: str,
        context: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行指定工具
        根据 tool type 路由到对应执行器
        """
        icon = self._icons.get(tool_id)
        if not icon:
            return {"success": False, "error": f"Tool not found: {tool_id}"}
        
        if icon.type == ToolType.MCP:
            return await self._execute_mcp(icon, context, parameters)
        elif icon.type == ToolType.SKILL:
            return await self._execute_skill(icon, context, parameters)
        elif icon.type == ToolType.ADAPTER:
            return await self._execute_adapter(icon, context, parameters)
        else:
            return {"success": False, "error": f"Unknown tool type: {icon.type}"}
    
    async def _execute_mcp(self, icon: ToolIcon, context: Dict, parameters: Optional[Dict]) -> Dict[str, Any]:
        """执行 MCP Tool"""
        self._init_mcp()
        if self._mcp_registry is None:
            return {"success": False, "error": "MCP not available"}
        
        config = icon.config
        result = await self._mcp_registry.call_tool(
            server_name=config["server_name"],
            tool_name=config["tool_name"],
            parameters=parameters or config.get("parameters", {})
        )
        
        return {
            "success": result.success,
            "result": result.data if hasattr(result, 'data') else result,
            "error": result.error if hasattr(result, 'error') and not result.success else None,
            "type": "mcp"
        }
    
    async def _execute_skill(self, icon: ToolIcon, context: Dict, parameters: Optional[Dict]) -> Dict[str, Any]:
        """执行 Skill"""
        self._init_skills()
        if self._skill_registry is None:
            return {"success": False, "error": "Skill registry not available"}
        
        config = icon.config
        skill_id = config["skill_id"]
        # 只使用字典类型的 parameters，避免 config.get("parameters") 返回 SkillParameter 列表导致解包错误
        params = parameters if isinstance(parameters, dict) else {}
        
        try:
            if hasattr(self._skill_registry, 'execute'):
                result = await self._skill_registry.execute(
                    skill_id,
                    **params
                )
                return {
                    "success": getattr(result, 'success', True),
                    "result": getattr(result, 'data', result),
                    "error": getattr(result, 'error', None),
                    "type": "skill"
                }
            else:
                skill = self._skill_registry.get(skill_id)
                if skill and hasattr(skill, 'run'):
                    result = await skill.run(**params)
                    return {
                        "success": getattr(result, 'success', True),
                        "result": getattr(result, 'data', result),
                        "error": getattr(result, 'error', None),
                        "type": "skill"
                    }
                else:
                    return {"success": False, "error": f"Skill execution not available: {skill_id}"}
        except Exception as e:
            return {"success": False, "error": str(e), "type": "skill"}
    
    async def _execute_adapter(self, icon: ToolIcon, context: Dict, parameters: Optional[Dict]) -> Dict[str, Any]:
        """执行 Adapter"""
        config = icon.config
        adapter_type = config.get("adapter_type")
        
        if adapter_type not in self._adapters:
            return {"success": False, "error": f"Adapter not found: {adapter_type}"}
        
        adapter = self._adapters[adapter_type]
        action = (parameters or {}).get("action", "detect_state")
        
        try:
            if action == "detect_state":
                result = await adapter.detect_state()
            elif hasattr(adapter, f"execute_action"):
                result = await adapter.execute_action(action, parameters or {})
            else:
                return {"success": False, "error": f"Action not supported: {action}"}
            
            return {
                "success": True,
                "result": result,
                "type": "adapter"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "type": "adapter"}


# 全局注册表实例
tool_registry = ToolRegistry()
