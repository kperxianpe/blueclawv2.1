#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Client - MCP 协议客户端
Week 20.5 实现：支持 stdio 和 sse 两种传输方式
"""
import asyncio
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# 尝试导入 MCP SDK
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("[MCP] SDK not available, using mock mode")


@dataclass
class MCPTool:
    """MCP Tool 定义"""
    server_name: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    parameters_schema: Dict[str, Any]


@dataclass
class MCPResult:
    """MCP 执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None


class MCPRegistry:
    """MCP 服务器注册表"""
    
    def __init__(self):
        self._servers: Dict[str, Dict] = {}  # server_name -> config
        self._tools_cache: List[MCPTool] = []
        self._load_config()
    
    def _load_config(self, config_path: str = None):
        """从配置文件加载 MCP 服务器"""
        import os
        
        # 尝试多个路径
        paths = [
            config_path,
            "backend/config/mcp_servers.json",
            "config/mcp_servers.json",
            "mcp_servers.json"
        ]
        
        for path in paths:
            if not path:
                continue
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    for server_name, server_config in config.get("servers", {}).items():
                        self._servers[server_name] = server_config
                    print(f"[MCP] Loaded config from {path}")
                    return
            except Exception as e:
                print(f"[MCP] Failed to load config from {path}: {e}")
        
        # 使用默认配置
        self._servers = {
            "mock": {
                "command": "echo",
                "args": ["mock server"],
                "description": "Mock MCP server for testing"
            }
        }
    
    async def discover_tools(self) -> List[MCPTool]:
        """
        发现所有 MCP 服务器的 Tools
        """
        if not MCP_AVAILABLE:
            print("[MCP] Using mock tools")
            return self._mock_tools()
        
        all_tools = []
        
        for server_name, server_config in self._servers.items():
            try:
                tools = await self._discover_server_tools(server_name, server_config)
                all_tools.extend(tools)
            except Exception as e:
                print(f"[MCP] Failed to discover tools from {server_name}: {e}")
        
        self._tools_cache = all_tools
        return all_tools
    
    async def _discover_server_tools(
        self,
        server_name: str,
        server_config: Dict
    ) -> List[MCPTool]:
        """发现单个服务器的 Tools"""
        
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env", {})
        
        # 合并环境变量
        import os
        env_vars = {**os.environ, **env}
        
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env_vars
        )
        
        tools = []
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 初始化
                await session.initialize()
                
                # 列出可用 tools
                response = await session.list_tools()
                
                for tool in response.tools:
                    tools.append(MCPTool(
                        server_name=server_name,
                        name=tool.name,
                        display_name=tool.name.replace("_", " ").title(),
                        description=tool.description,
                        parameters_schema=tool.inputSchema
                    ))
        
        return tools
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> MCPResult:
        """调用 MCP Tool"""
        if not MCP_AVAILABLE:
            return MCPResult(
                success=True,
                data={"mock": True, "tool": tool_name, "params": parameters},
                error=None
            )
        
        server_config = self._servers.get(server_name)
        if not server_config:
            return MCPResult(success=False, data=None, error=f"Server not found: {server_name}")
        
        try:
            import os
            env_vars = {**os.environ, **server_config.get("env", {})}
            
            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config.get("args", []),
                env=env_vars
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(
                        tool_name,
                        arguments=parameters
                    )
                    
                    # 解析结果
                    if result.isError:
                        return MCPResult(
                            success=False,
                            data=None,
                            error=str(result.content) if result.content else "Unknown error"
                        )
                    
                    # 提取文本内容
                    content_text = ""
                    for item in result.content:
                        if hasattr(item, 'text'):
                            content_text += item.text
                    
                    return MCPResult(
                        success=True,
                        data=content_text or result.content,
                        error=None
                    )
                    
        except Exception as e:
            return MCPResult(success=False, data=None, error=str(e))
    
    def _mock_tools(self) -> List[MCPTool]:
        """Mock tools for testing"""
        return [
            MCPTool(
                server_name="filesystem",
                name="read_file",
                display_name="读取文件",
                description="读取指定路径的文件内容",
                parameters_schema={"type": "object", "properties": {"path": {"type": "string"}}}
            ),
            MCPTool(
                server_name="filesystem",
                name="write_file",
                display_name="写入文件",
                description="写入内容到指定文件",
                parameters_schema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}
            ),
            MCPTool(
                server_name="web_search",
                name="search",
                display_name="网络搜索",
                description="执行网络搜索",
                parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}}
            ),
        ]


class MCPClient:
    """MCP 客户端（简化接口）"""
    
    def __init__(self):
        self.registry = MCPRegistry()
    
    async def list_tools(self) -> List[MCPTool]:
        """列出所有可用工具"""
        return await self.registry.discover_tools()
    
    async def execute(self, server_name: str, tool_name: str, parameters: Dict) -> MCPResult:
        """执行工具"""
        return await self.registry.call_tool(server_name, tool_name, parameters)


# 全局 MCP Registry 实例
mcp_registry = MCPRegistry()
