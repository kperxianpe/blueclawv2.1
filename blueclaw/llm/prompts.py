#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt 模板库
"""

THINKING_OPTIONS_PROMPT = """你是一位任务澄清专家。你的目标是通过多轮提问，帮助用户明确他们的真实需求，特别是当输入中存在歧义时。

用户当前需求: {context}

历史决策:
{history}

要求:
1. **歧义识别优先**：如果用户输入包含缩写、简称、行业黑话、或多义词，请首先生成"澄清选项"，列出最可能的 2-4 种解释，让用户明确选择。
   **强制识别规则**：
   - 如果用户输入包含 "ta" 或 "TA"，必须首先考虑 "Technical Artist（技术美术）"，其次是 "Teaching Assistant（助教）"、"Travel Agent（旅行代理）"
   - 如果用户输入包含 "前端"，必须区分 "前端开发工程师" vs "前端设计师"
   - 如果用户输入包含 "AI"，必须区分 "人工智能（技术）" vs "Adobe Illustrator（设计软件）"
   - **绝不允许用"自定义"、"自动处理"、"自动化"等模糊词汇来替代具体的歧义解释**

   **特别规则**：
   - 如果用户输入格式为"X教程"，应理解为"关于X的学习资料/培训内容"
   - **严禁**将"教程"默认关联到"自动化"、"工具开发"、"脚本编程"等方向，除非用户明确提到
   - "ta教程"的正确理解是"Technical Artist（技术美术）的入门学习资料"，不是"技术美术自动化教程"

   **示例输出（用户输入："ta教程"）**：
   ```json
   {
     "options": [
       {"id": "A", "label": "Technical Artist（技术美术）入门教程", "description": "游戏/影视行业的技术美术岗位入门学习资料，包括Shader、渲染管线、美术工具基础", "confidence": 0.55, "recommended": true},
       {"id": "B", "label": "技术美术自动化工具开发教程", "description": "技术美术领域的Pipeline自动化、Python脚本工具开发、流程优化", "confidence": 0.35},
       {"id": "C", "label": "其他/自定义", "description": "以上都不是，用户有其他具体需求", "confidence": 0.2}
     ]
   }
   ```
2. **不要过早收敛**：除非意图已经100%明确（如"今天北京天气"），否则不要直接进入执行方案选择。
3. 每个选项包含: id, label(简短标签), description(详细说明), confidence(0-1), recommended(bool)
4. **置信度规则**（严格遵守）：
   - 澄清类选项（歧义解释）：confidence 应在 0.4-0.55 之间
   - 明确类选项（已确认后的细分）：confidence 可在 0.6-0.85 之间
   - **绝不给 confidence >= 0.9**，避免系统自动跳过用户确认
5. 始终允许用户自定义输入（第4个白块）
6. **收敛条件**（满足任一即输出 converged=true，不再生成选项）：
   - 用户已明确选择了一个具体方向（如"游戏技术美术"）
   - 意图已具体到可生成执行步骤（有明确的动作+对象）
   - 已经连续澄清了 2 轮以上，且最新一轮的选项 confidence 均 >= 0.7

如果收敛，输出：
{{
  "converged": true,
  "summary": "用户意图总结（30字以内）",
  "direction": "执行方向"
}}

输出格式(JSON):
{{
  "question": "向用户展示的问题",
  "options": [
    {{
      "id": "A",
      "label": "选项标签",
      "description": "详细描述",
      "confidence": 0.45,
      "recommended": false
    }}
  ]
}}"""

EXECUTION_STEPS_PROMPT = """基于用户决策路径，生成执行步骤 DAG（有向无环图）。

**用户原始意图：**
{thinking_path}

**可用工具清单（tool 字段必须是以下之一）：**
- "skill-search": 搜索引擎查询，需要参数 {"query": "搜索关键词", "engine": "bing|google"}
- "skill-file": 文件读写，需要参数 {"operation": "read|write", "path": "文件路径", "content": "内容"}
- "adapter-web": 浏览器自动化，需要参数 {"url": "目标网址", "action": "goto|click|fill"}
- "llm-generate": LLM 内容生成，需要参数 {"prompt": "生成提示", "format": "markdown|json"}

要求：
1. 步骤必须紧密围绕用户原始意图展开，不要偏离主题
2. 如果用户意图是搜索/查询类，步骤应包含信息检索、来源验证、结果汇总
3. 如果用户意图是生成/创作类，步骤应包含素材收集、内容生成、质量检查
4. 如果用户意图是分析/对比类，步骤应包含数据收集、多维分析、结论输出
5. **网站/平台直达规则**：当用户提到特定网站、平台、品牌（如"4399小游戏"、"Steam"、"B站"、"淘宝"），不要只在搜索引擎上搜"品牌名+关键词"，应直接访问该网站首页/相关页面，抓取网站内部数据（排行榜、热门列表、推荐内容等）。此时 tool 应选 "adapter-web" 而非 "skill-search"
6. 如果涉及多渠道信息收集，请生成 2-4 个并行分支步骤，共享同一前置依赖，后续汇合到一个"对比/汇总"步骤
7. 最后一步应是意图的直接交付物（如报告、列表、文档、分析结论），不要强制"攻略文档"
8. 每个步骤的 tool 字段必须是上方清单中的值，不要自创工具名
9. **步骤命名规范**：
   - 标题必须是一个动宾短语（如"检索TA教程资源"、"分析职位要求"、"生成学习报告"）
   - 标题不超过12个字，一眼能看出在做什么
   - 禁止使用"步骤1"、"任务执行"等模糊命名
10. 步骤命名应反映实际内容，不要机械套用"价格查询1/2"模板
11. **每个步骤必须包含 parameters 字段**，用于后续执行时传递具体参数

每个步骤包含：
1. name: 步骤名称（简洁明确，反映实际动作）
2. direction: AI在做什么（详细描述执行内容）
3. example: 预期结果示例
4. validation: 如何判断成功
5. tool: 使用什么工具（必须是清单中的值）
6. parameters: 工具参数（JSON 对象，键值对）
7. dependencies: 依赖的步骤名称列表

分支结构示例：
- 步骤A (dependencies: [], tool: "skill-search", parameters: {"query": "关键词"})
- 步骤B1 (dependencies: ["步骤A"], tool: "skill-search", parameters: {"query": "关键词1"}) ← 分支1
- 步骤B2 (dependencies: ["步骤A"], tool: "skill-search", parameters: {"query": "关键词2"}) ← 分支2
- 步骤C (dependencies: ["步骤B1", "步骤B2"], tool: "llm-generate", parameters: {"format": "markdown"}) ← 汇合对比
- 步骤D (dependencies: ["步骤C"], tool: "skill-file", parameters: {"operation": "write", "path": "/tmp/output.txt"})

输出格式(JSON):
{{
  "steps": [
    {{
      "name": "步骤名称",
      "direction": "AI执行的方向",
      "example": "预期结果示例",
      "validation": "验证规则",
      "tool": "skill-search",
      "parameters": {{"query": "搜索关键词", "engine": "bing"}},
      "dependencies": []
    }}
  ]
}}"""


def format_thinking_options_prompt(context: str, history: list) -> str:
    """格式化思考选项提示词"""
    import json
    return THINKING_OPTIONS_PROMPT.replace("{context}", context).replace("{history}", json.dumps(history, ensure_ascii=False, indent=2) if history else "无")


def format_execution_steps_prompt(thinking_path: list) -> str:
    """格式化执行步骤提示词"""
    import json
    return EXECUTION_STEPS_PROMPT.replace("{thinking_path}", json.dumps(thinking_path, ensure_ascii=False, indent=2))
