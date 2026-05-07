# Blueclaw v2.1 参数调试报告

> 生成时间: 2026-04-29 20:30  
> 测试任务: "4399小游戏最火的游戏是哪个"  
> 后端版本: 2.5

---

## 一、调试方法

本轮参数调试采用**"问题驱动 + 根因定位 + 最小改动"**的方法论：

1. **提交测试任务** → 观察执行行为（截图 + 日志）
2. **发现异常** → 定位根因（代码审查 + 日志分析）
3. **最小修复** → 只改必要参数/代码，不改架构
4. **重启验证** → 重新提交相同任务，对比前后差异
5. **重复循环**直至执行正常化

**测试环境:**
- 后端: `python3 -m backend.main` (端口 8006)
- 前端: `vite preview --port 5173`
- 测试工具: Playwright headless + 截图验证
- LLM: Moonshot API (`moonshot-v1-8k`)

---

## 二、调整的参数清单

| # | 参数/代码位置 | 调整内容 | 调整前 | 调整后 | 验证结果 |
|---|--------------|---------|--------|--------|---------|
| 1 | `execution_engine.py` `_execute_tool()` | 新增 `_sanitize_search_query()` | `query = parameters.get("query", step.direction)` 原封不动塞进 Bing | 去掉动词前缀/后缀，超过30字截断，加 `site:csdn.net` | ✅ Bing 搜索栏不再出现整段描述 |
| 2 | `prompts.py` `EXECUTION_STEPS_PROMPT` | 新增第5条规则 | 无网站直达规则，LLM 用 `skill-search` 搜"品牌名+关键词" | 当用户提到特定网站/平台时，tool 选 `adapter-web` 直接访问 | ✅ LLM 生成 `adapter_web` 步骤访问 4399.com |
| 3 | `execution_engine.py` `_execute_tool()` `adapter_web` 分支 | action 匹配逻辑 | `if action == "goto" and url:` 只认 `"goto"` | `should_navigate = bool(url) and action not in ["", None, "screenshot", "click", "fill"]` | ✅ `visit`/`get_online_games` 等非标准 action 触发真实导航 |
| 4 | `execution_engine.py` `_execute_tool()` | WebAdapter auto-init | 并行步骤执行时 WebAdapter 未初始化，返回 `No WebAdapter available` | 任务级 `_task_adapter_map` 检测 + 自动 `adapter.init()` | ✅ 并行步骤前自动初始化 |
| 5 | `execution_engine.py` 新增 `_clean_html()` | HTML 清洗截断 | 整页 HTML（235K字符）直接传给 Phase 3 LLM | 去掉 script/style/head，保留纯文本，截断至 3000 字符 | ✅ `235K → 3K`，Phase 3 正常执行 |
| 6 | `execution_engine.py` Phase 3 prompt | Screenshot 过滤 | `tool_result` 完整传给 LLM，包含 screenshot base64（211K字符） | 过滤 screenshot 字段：`{k: v for k, v in tool_result.items() if k != "screenshot"}` | ✅ Prompt 长度 `3354` 字符，无 400 Bad Request |
| 7 | `execution_engine.py` `_execute_tool()` | Scroll action 修复 | `scroll` 被错误归入 `should_navigate` 排除列表，返回失败 | 新增 `action == "scroll"` 独立分支，支持 `selector` 和默认滚动 | ✅ Scroll 操作正常执行 |

---

## 三、调整前后详细对比

### 3.1 搜索关键词后处理

**调整前:**
```python
query = parameters.get("query", step.direction)
# step.direction = "检索技术美术在游戏行业的职位要求信息"
# query = "检索技术美术在游戏行业的职位要求信息" (整段塞进 Bing)
```

**调整后:**
```python
query = self._sanitize_search_query(raw_query, step.name)
# → 去掉"检索"前缀
# → 去掉"的信息"后缀
# → 超过30字截断到25字
# → 加 site:csdn.net
# 结果: "技术美术 游戏行业 职位要求 site:csdn.net"
```

**验证:** 日志 `Search query sanitized: '检索...' -> '技术美术...'`

---

### 3.2 Prompt 网站/平台直达规则

**调整前:**
```
用户: "4399小游戏最火的游戏是哪个"
LLM 生成: skill_search, query="PC网络游戏 在线人数最多 4399"
→ Bing 搜索，搜不到 4399 网站内部排行榜
```

**调整后 (prompt 新增第5条):**
```markdown
当用户提到特定网站、平台、品牌（如"4399小游戏"），不要只在搜索引擎上搜"品牌名+关键词"，
应直接访问该网站首页/相关页面，抓取网站内部数据。此时 tool 应选 "adapter-web" 而非 "skill-search"。
```

**验证:**
```
Tool selected: adapter_web, params: {'url': 'https://www.4399.com', 'action': 'visit'}
```

---

### 3.3 WebAdapter action 不匹配

**调整前:**
```python
if action == "goto" and url:
    await adapter._page.goto(url, ...)
# LLM 生成 action="visit" → 条件不满足 → 跳过导航 → 页面保持 about:blank
# 然后返回 success=True → Phase 3 LLM 误以为成功 → 编造数据
```

**调整后:**
```python
should_navigate = bool(url) and action not in ["", None, "screenshot", "click", "fill"]
# action="visit" → should_navigate=True → 触发 goto
# 页面真实加载，返回 html_length=235761
```

---

### 3.4 WebAdapter auto-init

**调整前:**
```
并行步骤1: Tool selected: adapter_web → "No WebAdapter available"
并行步骤2: Tool selected: adapter_web → "No WebAdapter available"
并行步骤3: Tool selected: adapter_web → "No WebAdapter available"
```

**调整后:**
```python
if task_id not in mgr._task_adapter_map:
    adapter = mgr.get_adapter("web")
    if adapter._page is None:
        await adapter.init(adapter_bp)
        # → WebAdapter auto-initialized
```

---

### 3.5 HTML 清洗截断

**调整前:**
```
Phase 3 prompt 包含:
- task_context (约 500 字)
- tool_result["html_length"] = 235761 字符
- prompt 模板
→ 总长度远超 8K 限制 → 400 Bad Request
```

**调整后:**
```python
def _clean_html(self, html: str, max_chars: int = 3000) -> str:
    # 去掉 script/style/head 标签
    # 去掉 HTML 标签保留纯文本
    # 合并空白，去掉噪声词
    # 截断至 3000 字符

# 结果: "WebAdapter loaded 235761 chars, cleaned to 3019 chars"
# Phase 3 prompt length: 3354 (正常范围)
```

---

### 3.6 Screenshot 过滤

**调整前:**
```python
result_prompt = create_execution_result_prompt(
    task_context=task_context,
    step_name=step.name,
    tool_result=tool_result  # ← 包含 screenshot: "data:image/jpeg;base64,/9j/4AAQ..." (211K)
)
```

**调整后:**
```python
tool_result_for_llm = {k: v for k, v in tool_result.items() if k != "screenshot"}
result_prompt = create_execution_result_prompt(
    task_context=task_context,
    step_name=step.name,
    tool_result=tool_result_for_llm  # ← 不含 screenshot
)
```

---

### 3.7 Scroll action 修复

**调整前:**
```python
should_navigate = bool(url) and action not in ["", None, "screenshot", "click", "fill", "scroll"]
# action="scroll" → should_navigate=False → 跳过所有分支 → 返回 "No WebAdapter available"
```

**调整后:**
```python
should_navigate = bool(url) and action not in ["", None, "screenshot", "click", "fill"]
# scroll 从排除列表去掉

# 新增独立分支:
if action == "scroll":
    selector = parameters.get("selector", "")
    if selector:
        await adapter._page.evaluate(f"document.querySelector('{selector}').scrollIntoView()")
    else:
        await adapter._page.evaluate("window.scrollBy(0, 500)")
    return {"success": True, "action": "scroll"}
```

---

## 四、验证结果

### 4.1 截图证据

| 截图文件 | 内容 | 状态 |
|---------|------|------|
| `v_4399_final_01.png` | Execution 蓝图整体，15 个节点，标题清晰 | ✅ |
| `v_4399_final_02_web.png` | Web 标签显示 4399.com 排行榜真实内容 | ✅ |
| `v_4399_web_02_web_tab.png` (修复前) | Web 标签显示 `about:blank` | ❌ (对比用) |

### 4.2 日志证据

```
[ExecutionEngine] WebAdapter navigating to: http://www.4399.com/
[ExecutionEngine] WebAdapter loaded 235761 chars, cleaned to 3019 chars, screenshot 211096 bytes
[ExecutionEngine] Phase 3 prompt length: 3354, preview: 请根据以下工具执行结果生成最终回复...
[ExecutionEngine] KimiCode-style result text generated: 基于访问4399小游戏平台首页获取的实时信息...
```

### 4.3 关键指标

| 指标 | 调整前 | 调整后 | 改善 |
|------|--------|--------|------|
| Bing 搜索栏内容 | 整段任务描述 | 精炼关键词 | 质量提升 |
| 4399.com 访问 | `about:blank` | 真实首页加载 | 从失败到成功 |
| Phase 3 prompt 长度 | > 200,000 字符 | 3,354 字符 | -98% |
| Moonshot API 400 错误 | 频繁出现 | 完全消失 | 稳定性提升 |
| WebAdapter 初始化 | 手动/缺失 | 自动 per-task | 可靠性提升 |
| Scroll 操作 | 不支持 | 支持 selector/默认滚动 | 功能补全 |

---

## 五、总结

本轮参数调试的核心主题是**"adapter 执行常规化"**——让 Blueclaw 的 WebAdapter 执行质量达到 OpenClaw 级别的稳定性。

**关键洞察:**
1. **Prompt 策略比代码更重要** — 加一条"网站直达规则"比改 adapter 逻辑更有效
2. **数据截断是 400 的根因** — 不是 HTML 太长，是 screenshot base64 太长
3. **Auto-init 是并行执行的前提** — WebAdapter 必须任务级生命周期管理
4. **Action 规范化比严格匹配更鲁棒** — LLM 会生成非标准 action 名称

**下一步建议:**
- 测试更多网站直达场景（Steam、B站、淘宝等）
- 验证 HTML 清洗是否丢失关键内容（如排行榜数据）
- 考虑 screenshot 压缩/缩略图方案，替代完全过滤
- 补充更多浏览器交互操作（hover、select、wait）

---

*文档生成时间: 2026-04-29 20:30*  
*对应后端 PID: 755895 (debug run)*  
*对应截图: `screenshots/verify/v_4399_final_*.png`*
