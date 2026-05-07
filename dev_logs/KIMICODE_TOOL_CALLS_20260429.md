## KimiCode-style Tool Calling 集成报告

### 2026-04-29 11:20 — 集成完成

**修改文件：**
1. `blueclaw/llm/tool_calls.py` — 新建，包含：
   - `TOOLS_SCHEMA`: 4 个工具的结构化 JSON Schema 定义（skill_search, skill_file, adapter_web, llm_generate）
   - `create_tool_call_prompt()`: Phase 1 提示词，让 LLM 自动选择工具和提取参数
   - `create_execution_result_prompt()`: Phase 3 提示词，回传工具结果给 LLM 生成最终回复
   - `TOOL_PARAMETER_RULES`: 搜索关键词提炼规则（去掉动词/修饰语，自动加 site:csdn.net）

2. `blueclaw/core/execution_engine.py` — 修改：
   - `_execute_step_legacy()`: 改为 KimiCode-style 三阶段执行
     - Phase 1: LLM 选择工具 + 提取参数
     - Phase 2: 执行工具（搜索/浏览器/文件/生成）
     - Phase 3: LLM 根据工具结果生成最终回复
   - `_execute_step_legacy_fallback()`: 原逻辑作为 fallback
   - `_execute_tool()`: 具体工具执行器

**KimiCode 机制对比：**

| 特性 | KimiCode | Blueclaw (新) |
|------|----------|---------------|
| 工具定义 | JSON Schema (tools 参数) | `TOOLS_SCHEMA` 列表 |
| 工具选择 | LLM 自动选择 (finish_reason=tool_calls) | Phase 1 LLM 选择 + 参数提取 |
| 参数提取 | 自动从上下文提取 | LLM 根据规则提取 |
| 执行流程 | 调用 → 执行 → 结果回传 → 生成回复 | Phase 1 → 2 → 3 |
| 多工具并行 | 支持多个 tool_calls | 当前单工具，可扩展 |

**下一步：**
- 重启后端测试新的工具调用流程
- 验证搜索关键词是否自动提炼
- 验证 WebAdapter 截图是否正常

**当前状态：**
- 代码已修改，待重启后端测试
- 429 限流仍需注意，测试间隔保持 30 秒以上
