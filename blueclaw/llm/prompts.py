#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt 模板库
"""

THINKING_OPTIONS_PROMPT = """你是一个智能助手。用户当前需求: {context}

请生成3-4个选项供用户选择，帮助逐步明确需求。

要求:
1. 每个选项有标签(简短)和描述(详细)
2. 给出置信度(0-1)，标记最推荐的选项
3. 选项应该涵盖不同的处理方式

输出格式(JSON):
{{
  "question": "向用户展示的问题",
  "options": [
    {{
      "id": "A",
      "label": "选项标签",
      "description": "详细描述",
      "confidence": 0.95,
      "recommended": true
    }}
  ]
}}"""

EXECUTION_STEPS_PROMPT = """基于用户决策路径，生成执行步骤 DAG（有向无环图）。

决策路径:
{thinking_path}

要求:
1. 步骤必须覆盖信息检索、价格查询、方案对比、最终输出
2. 必须包含至少一个"查价格"或"预算分析"相关的步骤
3. 必须包含至少一个"对比价格方案"或"汇总对比"相关的步骤
4. 最后一步必须是"生成可视文档"或"输出攻略文档"，生成结构化的Markdown文档
5. 每个步骤的 tool 字段必须是具体的 Skill 名称
6. **如果信息检索或数据收集可以从多个不同渠道并行进行（例如：查不同交通方式、查不同学校分数线、查不同住宿方案等），请显式生成 2-4 个并行分支步骤**。这些分支步骤共享同一个前置依赖（dependencies 相同），并在后续汇合到一个"对比/汇总"步骤
7. **汇合步骤的 dependencies 必须同时包含所有并行分支步骤的名称**，以体现分支合并

每个步骤包含:
1. name: 步骤名称（简洁明确）
2. direction: AI在做什么（详细描述执行内容）
3. example: 预期结果示例
4. validation: 如何判断成功
5. tool: 使用什么工具（Skill名称）
6. dependencies: 依赖的步骤名称列表（使用前置步骤的name）

分支结构示例:
- 步骤A (dependencies: [])
- 步骤B1 (dependencies: ["步骤A"])  ← 分支1
- 步骤B2 (dependencies: ["步骤A"])  ← 分支2
- 步骤C (dependencies: ["步骤B1", "步骤B2"])  ← 汇合对比
- 步骤D (dependencies: ["步骤C"])

输出格式(JSON):
{{
  "steps": [
    {{
      "name": "步骤名称",
      "direction": "AI执行的方向",
      "example": "预期结果示例",
      "validation": "验证规则",
      "tool": "SkillName",
      "dependencies": []
    }}
  ]
}}"""


def format_thinking_options_prompt(context: str, history: list) -> str:
    """格式化思考选项提示词"""
    return THINKING_OPTIONS_PROMPT.format(context=context)


def format_execution_steps_prompt(thinking_path: list) -> str:
    """格式化执行步骤提示词"""
    import json
    return EXECUTION_STEPS_PROMPT.format(
        thinking_path=json.dumps(thinking_path, ensure_ascii=False, indent=2)
    )
