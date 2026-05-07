# Blueclaw v2.1 Prompt & Skill 参数调试分析报告

**日期**: 2026-04-29
**状态**: 代码冻结，仅参数/提示词调优
**范围**: Thinking Prompt → Execution Blueprint Prompt → Step Execution Prompt → Adapter Search Prompt

---

## 一、核心问题汇总（用户已感知到的）

### 1.1 Bing 搜索栏输入整句提示词，而非关键词

**现象**: WebAdapter 执行搜索步骤时，地址栏是 `https://www.bing.com/search?q=收集技术美术基本信息`（一整句话），而不是 `ta教程 site:csdn.net` 或 `Technical Artist tutorial`。

**根因定位**:
```python
# execution_engine.py: ~line 577
search_url = f'https://www.bing.com/search?q={quote_plus(query)}'
# 其中 query = step.direction = "收集技术美术基本信息"
```

`step.direction` 是 LLM 生成的"执行方向描述"（如"收集技术美术基本信息"），而不是**搜索关键词**。这相当于让 Bing 搜索一句自然语言描述，而不是精炼的搜索词。

**对比 OpenClaw 正常流程**:
- OpenClaw Skill 系统有明确的参数模板：`{{query}}` 由 Skill 的 `parameters` 定义
- Skill 的 `query` 参数通常由 **LLM 从用户意图中提炼关键词** 后填入，或直接使用用户原始输入中的关键词部分
- 不会把"执行方向说明文字"直接塞进搜索框

---

### 1.2 缺乏提示词生成规范 — "想到哪写到哪"

**现状问题**:

| Prompt | 问题 |
|--------|------|
| `THINKING_OPTIONS_PROMPT` | 虽然有歧义识别规则，但缺乏"何时停止澄清"的明确边界条件 |
| `EXECUTION_STEPS_PROMPT` | 要求生成 DAG，但没有提供工具清单，LLM 只能猜 "Skill" / "Browser" |
| `_execute_step_legacy` | Prompt 过于自由："请根据用户原始需求和步骤信息，生成具体的执行结果" — 无格式约束、无输出规范 |
| `_execute_step_with_binding` (skill-search) | 直接 `parameters["query"] = step.direction`，无关键词提炼逻辑 |
| `_execute_with_bound_tool` (skill-file write) | Doc prompt 要求生成 Markdown，但没有指定长度、结构深度、必须包含的字段 |

**OpenClaw 对比**:
- OpenClaw Skill 有 `parameters` schema（name/type/default/required/description）
- Skill 的 SKILL.md 里有明确的"输入 → 处理 → 输出"流程
- Skill 通过 `{{variable}}` 模板精确控制 LLM 输出格式
- OpenClaw Agent 调用 Skill 时，参数是**结构化**的，不是自然语言描述

---

### 1.3 Tool 绑定过于粗糙 — 关键词匹配而非语义理解

**现状**:
```python
# execution_engine.py create_blueprint()
if any(k in lowered for k in ["搜索", "查找", "查询", "查", "网页", "浏览器", "web", "browser"]):
    step.tool = "Browser"
```

这是**字符串关键词匹配**，不是语义理解。例如：
- "查询数据库状态" → 误判为 Browser（应该是 SQL skill）
- "浏览器兼容性检查" → 误判为 Browser（其实是分析任务）
- "搜索内存泄漏原因" → 应该先用 LLM 分析，再决定是 search 还是 code analysis

**OpenClaw 对比**:
- OpenClaw 的 ToolSelector 基于 tool 的 `description` + `hint` 做语义匹配
- 或者 Skill 自身在 SKILL.md 里声明 `When to use`
- 不是简单的关键词包含判断

---

## 二、四层 Prompt 逐层分析

### 2.1 Layer 1: Thinking Options Prompt（思考蓝图）

**当前** (`prompts.py`):
```
歧义识别优先、不要过早收敛、confidence 规则、输出 JSON
```

**问题**:
1. **无停止条件**: 规则说"不要过早收敛"，但没说"何时必须收敛"。导致 MAX_DEPTH=5 时可能仍不收敛，或歧义极少时仍强行多轮。
2. **Confidence 规则与 threshold 脱节**: Prompt 要求澄清类 0.5-0.7，但代码 threshold=0.50。如果 LLM 严格遵守 prompt 给 0.6，threshold 0.50 会 auto-select；如果 LLM 不遵守给 0.95，threshold 0.50 更会 auto-select。
3. **无 history 长度限制**: history 用 `json.dumps(..., indent=2)` 传入，5 轮后可能很长，占用 token。

**改进方向**:
- 增加"收敛条件"："如果用户意图已经明确到可以生成具体执行步骤，则输出 `converged: true` 并给出总结"
- Confidence 规则与 threshold 统一：要么 threshold 降到 0.45 覆盖 0.5-0.7，要么 prompt 要求澄清类 0.3-0.5（确保低于 threshold）
- History 做摘要压缩：不是 raw JSON，而是"用户已确认：TA = Technical Artist（游戏方向）"

---

### 2.2 Layer 2: Execution Blueprint Prompt（执行蓝图生成）

**当前** (`prompts.py`):
```
基于用户决策路径，生成执行步骤 DAG...
要求：1.步骤围绕意图... 2.搜索类包含检索... 3.生成类包含素材...
每个步骤包含 name/direction/example/validation/tool/dependencies
```

**问题**:
1. **无可用工具清单**: LLM 不知道系统有哪些 skill（search/file/browser/code），只能猜 "Skill" 或 "Browser"。
2. **Tool 字段自由文本**: LLM 可能输出 "搜索引擎"、"浏览器"、"WebAdapter"、"Bing"，代码无法匹配。
3. **Direction 过于描述性**: "收集技术美术基本信息" 是一个方向描述，不是可执行指令。
4. **无参数规范**: 没有要求 LLM 输出每个步骤需要的参数（如 search 的 query、file 的 path）。

**改进方向**:
- **提供工具清单**: 在 prompt 里列出可用 tools：`["skill-search", "skill-file", "adapter-web", "llm-generate"]`
- **Tool 字段枚举**: 要求 `tool` 必须是清单中的一个，否则无效
- **Direction 拆分**: 拆为 `action`（做什么）+ `target`（对象）+ `constraints`（约束）
- **增加 parameters 字段**: 要求 LLM 输出每个步骤需要的参数键值对

**OpenClaw 对比**:
- OpenClaw 的 Skill 在 SKILL.md 里定义了清晰的输入参数
- Agent 调用时会把参数结构化传入，不是让 LLM 自由发挥

---

### 2.3 Layer 3: Step Execution Prompt（步骤执行）

**当前** (`execution_engine.py _execute_step_legacy`):
```python
prompt = f"""你正在执行一个任务步骤。
用户原始需求: {task_context}
步骤名称: {step.name}
步骤说明: {step.description}
执行方向: {step.direction}

请根据用户原始需求和步骤信息，生成具体的执行结果...
直接输出结果内容，不要添加任何解释。"""
```

**问题**:
1. **无输出格式约束**: "直接输出结果"导致 LLM 可能输出 JSON、Markdown、纯文本、甚至英文，不可控。
2. **无质量检查**: 没有要求 LLM 自检结果是否满足 validation 规则。
3. **Step 间无上下文传递**: 前一步的结果不会传给后一步，每一步都是独立调用 LLM。
4. **无错误处理指引**: 如果无法执行，LLM 应该输出什么？现在让它"生成结果"，它可能 hallucinate。

**改进方向**:
- **输出格式强制**: "输出必须是 Markdown，包含以下章节：..."
- **自检要求**: "生成结果后，请对照 validation 规则检查，如果不满足请说明原因"
- **上下文传递**: 在 prompt 中加入前序步骤的关键结果摘要
- **失败显式化**: "如果无法完成，输出 `FAILED: 原因`"

---

### 2.4 Layer 4: Adapter Execution Prompt（WebAdapter 搜索）

**当前** (`execution_engine.py _execute_with_bound_tool`):
```python
# skill-search 分支
query = parameters.get("query", step.direction)
search_url = f'https://www.bing.com/search?q={quote_plus(query)}'
```

**问题**:
1. **Query = Step.direction**: 整句描述直接当搜索词。
2. **无搜索引擎优化**: 没有 site:、没有引号精确匹配、没有排除词。
3. **无搜索词提炼步骤**: 没有让 LLM 先把 direction 提炼成 3-5 个关键词。
4. **硬编码 Bing**: 没有根据内容选择搜索引擎（代码查 CSDN → 用 site:csdn.net；查英文 → 用 Google）。

**改进方向**:
- **增加关键词提炼 prompt**: "将以下任务描述提炼为适合搜索引擎的 3-5 个关键词：{direction}"
- **搜索词模板化**: `"{keywords}" site:{preferred_site}` 或 `{keywords} -排除词`
- **搜索引擎选择**: 根据目标网站自动选择（中文技术 → Bing + site:csdn.net；英文 → Google）

---

## 三、与 OpenClaw 正常流程的对比

### 3.1 OpenClaw Skill 调用流程

```
用户输入 → Agent 理解意图 → 选择 Skill → 提取参数 → 执行 Skill → 返回结果
                ↓                ↓            ↓
            意图分类        SKILL.md    参数模板 {{}}
                            描述匹配     类型检查
```

**关键特征**:
1. **Skill 有明确的参数 Schema**: `parameters: [{name, type, required, default, description}]`
2. **参数由 Agent 从用户输入中提取**，不是让 LLM 在执行时自由生成
3. **Skill 有 `When to use` 描述**，Agent 据此判断该选哪个 Skill
4. **执行结果有明确格式**，通常由 Skill 的代码决定（不是 LLM 自由发挥）

### 3.2 Blueclaw 当前流程

```
用户输入 → Thinking Engine → Execution Blueprint → Step Execution → Adapter/LLM
                (LLM生成选项)     (LLM生成步骤)      (LLM生成结果)
                                    ↓
                              tool: "Browser"?  ← 关键词匹配
                              direction: 整句描述 ← 直接当搜索词
```

**关键差距**:
1. **没有参数提取层**: 用户输入 → 步骤 direction（描述性句子）→ 直接当参数用
2. **没有 Skill Schema**: tool 是自由文本，不是枚举值；parameters 是运行时推断，不是声明式
3. **LLM 过度承担**: 每个步骤都让 LLM "生成结果"，而不是调用确定性工具
4. **缺乏约束**: Prompt 没有严格的输出格式和错误处理要求

---

## 四、改进方案（参数调试方向）

### 4.1 短期：Prompt 层面调优（不改代码架构）

#### A. 搜索关键词提炼 Prompt

在 `execution_engine.py` 的 `skill-search` 分支前增加一层：

```python
# 新增：关键词提炼
keyword_prompt = f"""将以下任务描述提炼为适合搜索引擎的简短关键词（3-5个词）：
任务：{step.direction}
要求：
1. 去掉动词和修饰语，保留核心名词和术语
2. 如果是中文内容，优先保留中文关键词
3. 如果涉及特定网站，添加 site: 限定
4. 只输出关键词，不要解释

示例：
- 输入："收集技术美术在游戏行业的职位要求信息"
- 输出：技术美术 职位要求 游戏行业 site:csdn.net

输出："""

keywords = await LLMClient().quick_complete(keyword_prompt)
search_url = f'https://www.bing.com/search?q={quote_plus(keywords.strip())}'
```

#### B. Execution Blueprint Prompt 增加工具清单

```python
EXECUTION_STEPS_PROMPT = """...
可用工具清单（tool 字段必须是以下之一）：
- "skill-search": 搜索引擎查询，需要参数 {query}
- "skill-file": 文件读写，需要参数 {operation, path, content?}
- "adapter-web": 浏览器自动化，需要参数 {url, action}
- "llm-generate": LLM 内容生成，需要参数 {prompt, format}

每个步骤必须包含 parameters 字段：
"parameters": {"query": "搜索关键词", ...}
...
"""
```

#### C. Step Execution Prompt 增加格式约束

```python
_execute_step_legacy_prompt = f"""...
输出要求：
1. 使用 Markdown 格式
2. 必须包含以下章节：## 结果摘要、## 详细内容、## 信息来源
3. 如果涉及数据，使用表格呈现
4. 内容长度控制在 500-1000 字
5. 如果无法完成，首行必须是 `FAILED: 原因`

自检：生成后请检查是否满足 validation 规则：{step.validation}
..."""
```

#### D. Thinking Prompt 收敛条件明确化

```python
THINKING_OPTIONS_PROMPT = """...
收敛条件（满足任一即输出 converged=true）：
1. 用户已明确选择了一个具体方向（如"游戏技术美术"）
2. 意图已具体到可生成执行步骤（有明确的动作+对象）
3. 已经连续澄清了 2 轮以上，且最新一轮的选项 confidence 均 >= 0.8

如果收敛，输出：
{{
  "converged": true,
  "summary": "用户意图总结（50字以内）",
  "direction": "执行方向"
}}
...
"""
```

### 4.2 中期：引入 Skill Schema（轻量级）

在 `backend/tools/` 里增加一个简单的 Skill 注册表（不需要完整 OpenClaw Skill 系统）：

```python
# backend/tools/skill_schemas.py
SKILL_SCHEMAS = {
    "skill-search": {
        "description": "搜索引擎查询",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "搜索关键词"},
            "engine": {"type": "string", "default": "bing", "enum": ["bing", "google", "csdn"]},
        }
    },
    "skill-file": {
        "description": "文件操作",
        "parameters": {
            "operation": {"type": "string", "required": True, "enum": ["read", "write", "append"]},
            "path": {"type": "string", "required": True},
            "content": {"type": "string", "required": False},
        }
    },
}
```

然后在 `create_blueprint` 时把 Schema 放进 prompt，让 LLM 按 Schema 输出 parameters。

### 4.3 长期：对齐 OpenClaw Skill 机制

- 每个 Skill 有独立的 SKILL.md（描述 + 参数 + When to use）
- ToolSelector 基于语义匹配选择 Skill（不是关键词包含）
- 参数提取由 Agent 负责（不是 LLM 自由生成）
- 执行结果由 Skill 代码控制（不是 LLM 生成）

---

## 五、具体参数修改清单

### 5.1 Prompt 文件 (`blueclaw/llm/prompts.py`)

| 修改项 | 当前值 | 建议值 | 原因 |
|--------|--------|--------|------|
| `THINKING_OPTIONS_PROMPT` 收敛条件 | 无 | 增加 converged 条件 | 避免无限澄清 |
| `THINKING_OPTIONS_PROMPT` confidence 规则 | 澄清类 0.5-0.7 | 澄清类 0.3-0.5 | 确保低于 threshold 0.50 |
| `EXECUTION_STEPS_PROMPT` tool 字段 | 自由文本 | 枚举清单 | LLM 知道可用工具 |
| `EXECUTION_STEPS_PROMPT` | 无 parameters | 增加 parameters 字段 | 步骤可携带参数 |

### 5.2 Execution Engine (`blueclaw/core/execution_engine.py`)

| 修改项 | 当前代码 | 建议修改 |
|--------|----------|----------|
| `skill-search` query | `query = step.direction` | 增加关键词提炼层 |
| `skill-search` URL | 硬编码 Bing | 根据内容选择搜索引擎 |
| `_execute_step_legacy` prompt | 自由生成 | 增加格式约束 + 自检 |
| `create_blueprint` tool 绑定 | 关键词匹配 | 基于 LLM 输出的 tool 字段 |

### 5.3 阈值参数

| 参数 | 当前值 | 建议值 | 原因 |
|------|--------|--------|------|
| `AUTO_SELECT_THRESHOLD` | 0.50 | 0.45 | 配合 prompt 澄清类 confidence 0.3-0.5 |
| `MAX_DEPTH` | 5 | 5 | 保持不变，但收敛条件提前触发 |

---

## 六、验证方案

### 6.1 验证 "ta教程" 链路

**测试输入**: `"ta教程"`（关闭 auto_select）

**期望行为**:
1. Thinking 第1轮：澄清 "ta" = Technical Artist / Teaching Assistant / Travel Agent（confidence 0.4-0.5）
2. 用户选 A → Thinking 第2轮：游戏 TA vs 影视 TA（confidence 0.6-0.7）
3. 用户选 A → Thinking 收敛（converged=true, summary="游戏技术美术教程"）
4. Execution Blueprint:
   - Step 1: `tool="skill-search", parameters={query:"游戏技术美术教程 site:csdn.net", engine:"bing"}`
   - Step 2: `tool="llm-generate", parameters={prompt:"整理TA技能树", format:"markdown"}`
5. Step Execution: 搜索关键词是提炼后的 "游戏技术美术 教程 site:csdn.net"，不是整句方向描述

### 6.2 验证搜索质量

**检查项**:
- Bing 地址栏的 `q=` 参数是否 ≤10 个中文字符（精炼关键词）
- 是否包含 `site:csdn.net` 限定（如果意图是查中文技术内容）
- 搜索结果是否与 Technical Artist 相关（而非 Teaching Assistant）

---

## 七、结论

Blueclaw v2.1 的核心链路（Thinking → Execution → Adapter）已经打通，但**提示词工程（Prompt Engineering）和参数规范**是当前的明显短板。主要问题不是架构性的，而是**每一层 prompt 都过于自由，缺乏约束和结构化要求**。

与 OpenClaw 的差距本质是：**OpenClaw 的 Skill 系统提供了"参数 schema + 工具描述 + 执行代码"的三层约束，而 Blueclaw 当前把这三层都交给了 LLM 自由发挥**。

短期通过 prompt 调优可以显著改善（关键词提炼、工具清单、格式约束），中期引入轻量级 Skill Schema 可以对齐 OpenClaw 的确定性，长期建议逐步迁移到完整的 Skill 注册表机制。

---

*报告生成时间: 2026-04-29 03:28 CST*
*代码状态: 冻结（仅 prompt/参数调优）*
