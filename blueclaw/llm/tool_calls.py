#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KimiCode-style Tool Calling for Blueclaw

适配 KimiCode 的 tool_calls 机制：
1. 结构化工具定义（JSON Schema）
2. LLM 自动选择工具和提取参数
3. 执行结果回传 LLM 生成最终回复
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "skill_search",
            "description": """
                通过搜索引擎搜索互联网上的内容。
                
                当任务需要查找信息、资料、教程、文档时，调用此工具。
                请从任务描述中提取核心搜索词作为 query 参数。
                对于技术类中文内容，自动添加 site:csdn.net 或 site:juejin.cn 限定。
            """,
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，从任务描述中提取的核心名词和术语，去除动词和修饰语"
                    },
                    "engine": {
                        "type": "string",
                        "enum": ["bing", "google", "baidu"],
                        "description": "搜索引擎，默认 bing",
                        "default": "bing"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数，默认 10",
                        "default": 10
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "skill_file",
            "description": """
                文件读写操作。
                
                当任务需要读取文件内容、写入报告、保存数据时，调用此工具。
            """,
            "parameters": {
                "type": "object",
                "required": ["operation", "path"],
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "write", "append", "list"],
                        "description": "操作类型"
                    },
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "写入内容（write/append 时必填）"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adapter_web",
            "description": """
                浏览器自动化操作。
                
                当任务需要访问网页、点击按钮、填写表单、截图时，调用此工具。
                执行后会返回页面截图和 HTML 内容。
            """,
            "parameters": {
                "type": "object",
                "required": ["url", "action"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "目标网址"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["goto", "click", "fill", "screenshot", "scroll"],
                        "description": "浏览器动作"
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS 选择器（click/fill 时必填）"
                    },
                    "value": {
                        "type": "string",
                        "description": "填充值（fill 时必填）"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "llm_generate",
            "description": """
                LLM 内容生成。
                
                当任务需要总结、分析、生成报告、翻译、创作内容时，调用此工具。
                不需要联网，基于已有信息生成内容。
            """,
            "parameters": {
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "生成提示词"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json", "text"],
                        "description": "输出格式",
                        "default": "markdown"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "最大长度（字）",
                        "default": 800
                    }
                }
            }
        }
    }
]


def create_tool_call_prompt(step_name: str, step_direction: str, step_tool: str) -> str:
    """
    创建 KimiCode-style 的工具调用提示词
    
    让 LLM 自动选择工具并提取参数
    """
    return f"""你正在执行一个任务步骤，需要选择最适合的工具并提取参数。

步骤名称: {step_name}
步骤方向: {step_direction}
建议工具: {step_tool}

可用工具清单：
1. skill_search - 搜索引擎查询（需要参数: query, engine, max_results）
2. skill_file - 文件读写（需要参数: operation, path, content）
3. adapter_web - 浏览器自动化（需要参数: url, action, selector, value）
4. llm_generate - LLM 内容生成（需要参数: prompt, format, max_length）

请分析步骤方向，选择最合适的工具，并提取具体参数。

输出格式（严格JSON）：
{{
    "tool": "工具名称",
    "parameters": {{
        "参数名": "参数值"
    }},
    "reasoning": "选择此工具和参数的原因（50字以内）"
}}

要求：
1. tool 必须是上述4个之一
2. parameters 必须包含该工具的所有 required 参数
3. **关键：query 参数必须准确反映用户原始意图**
   - 如果用户要"教程"，query 必须包含"教程"或"学习资料"
   - 如果用户要"岗位"，query 才能包含"岗位"或"职位"
   - 去掉动词（检索、查找、搜索），保留核心名词
   - 示例："检索技术美术教程"→"技术美术 教程 site:csdn.net"
4. 直接输出JSON，不要添加任何解释"""


def create_execution_result_prompt(task_context: str, step_name: str, tool_result: dict) -> str:
    """
    创建执行结果生成提示词
    
    工具执行后，回传结果给 LLM 生成最终回复
    """
    return f"""用户原始需求: {task_context}
步骤名称: {step_name}
工具执行结果: {tool_result}

请根据工具执行结果，生成步骤的最终输出。

输出要求：
1. 使用 Markdown 格式
2. 必须包含：
   - ## 结果摘要（100字以内的核心结论）
   - ## 详细内容（具体信息、数据、分析）
   - ## 信息来源（数据来自哪里）
3. 如果工具执行失败，首行必须是 `FAILED: 具体原因`
4. 内容长度 300-800 字
5. 直接输出内容，不要添加解释"""


# 工具参数提取规则
TOOL_PARAMETER_RULES = {
    "skill_search": {
        "query_extraction": """
            将任务描述提炼为搜索关键词：
            1. 去掉动词（检索、查找、搜索、收集）
            2. 去掉修饰语（详细的、相关的、高质量的）
            3. 保留核心名词和术语
            4. 中文技术内容自动添加 site:csdn.net
            5. 多个关键词用空格分隔
            
            示例：
            - "检索技术美术在游戏行业的职位要求信息" → "技术美术 职位要求 游戏行业 site:csdn.net"
            - "查找Python自动化测试教程" → "Python 自动化测试 教程 site:juejin.cn"
            - "收集前端性能优化最佳实践" → "前端性能优化 最佳实践 site:csdn.net"
        """,
        "default_engine": "bing",
        "default_max_results": 10
    },
    "adapter_web": {
        "url_patterns": {
            "search": "https://www.bing.com/search?q={query}",
            "csdn": "https://so.csdn.net/so/search?q={query}",
            "bilibili": "https://search.bilibili.com/all?keyword={query}"
        }
    }
}
