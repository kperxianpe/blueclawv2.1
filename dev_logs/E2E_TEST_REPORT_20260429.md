# Blueclaw v2.1 全链路测试报告

**测试日期**: 2026-04-28 ~ 2026-04-29
**测试目标**: 验证 thinking 多轮交互 → execution 蓝图生成 → WebAdapter 执行 的完整链路
**测试任务**: "去CSDN搜索ta教程"
**测试环境**: 真实后端（非 mock），端口 8006/5173

---

## 一、本次修复的问题清单

### 1.1 严重问题 — WebSocket 连接崩溃（已修复）

**问题**: 后端 WebSocket 连接建立后立刻断开，前端永远收不到 thinking/execution 推送。

**根因**: `backend/unified_server.py` 第 53 行调用 `sys.stdout.flush()` 时抛出 `NameError: name 'sys' is not defined`，因为文件头部缺少 `import sys`。这个异常导致 FastAPI 的 WebSocket handler 崩溃、连接断开。

**修复**:
```python
# backend/unified_server.py 头部
import asyncio
import json
import sys        # ← 新增
import uuid
```

**验证**: 修复后 WebSocket 连接保持 120 秒以上，前端成功收到 `thinking.node_created`、`thinking.converged`、`execution.blueprint_loaded`、`execution.step_completed` 等全部消息。

---

### 1.2 Thinking 收敛后返回 None（已修复）

**问题**: `start_thinking()` 在 auto_select 模式下收敛后返回 None，导致 `_handle_task_start()` 无法推送节点。

**根因**: `start_thinking()` 调用 `select_option_impl()` 递归自动选择，当 `path_len >= MAX_DEPTH` 时返回 None。`_handle_task_start()` 判断 `if root_node:` 为 False，跳过 `push_thinking_node_created()`。

**修复**:
```python
# blueclaw/core/thinking_engine.py — start_thinking()
result = await self.select_option_impl(task_id, node.id, auto_option_id)
# 如果收敛了（select_option_impl 返回 None），返回最后一个节点
if result is None and self.is_converged(task_id):
    print(f"[ThinkingEngine] Auto-select converged, returning last node")
    node_ids = self.task_nodes.get(task_id, [])
    if node_ids:
        last_node = self.nodes.get(node_ids[-1])
        if last_node:
            return last_node
return result
```

**验证**: 修复后 `start_thinking()` 在收敛时返回最后一个节点，`_handle_task_start()` 成功调用 `push_thinking_node_created()`。

---

### 1.3 Thinking 收敛后未触发 Execution 蓝图（已修复）

**问题**: thinking 收敛后，execution 蓝图未自动生成，前端永远停留在 thinking 阶段。

**根因**: `_handle_task_start()` 只推送 `thinking.node_created`，没有检查节点是否已收敛，也没有触发 `_auto_generate_blueprint()`。

**修复**:
```python
# backend/websocket/message_router.py — _handle_task_start()
if root_node:
    await state_sync.push_thinking_node_created(task.id, root_node, is_root=True)
    
    # 如果节点已经收敛（auto_select 模式），自动生成蓝图
    if thinking_engine.is_converged(task.id):
        print(f"[DEBUG router] Thinking converged, auto-generating blueprint")
        final_path = thinking_engine.get_thinking_path(task.id)
        asyncio.create_task(self._auto_generate_blueprint(task.id, [...]))
```

**验证**: 修复后 thinking 收敛 2 秒内自动触发 `execution.blueprint_loaded`，前端切换到 execution 视图。

---

### 1.4 Execution 蓝图硬编码约束（已修复）

**问题**: 无论用户输入什么，execution 蓝图总是包含"价格查询1/2"和"预算分析"。

**根因**: `EXECUTION_STEPS_PROMPT` 模板中硬编码了"必须包含至少一个查价格或预算分析"和"最后一步必须是生成攻略文档"。

**修复**: 重写 `EXECUTION_STEPS_PROMPT`，去掉硬编码约束，改为根据 thinking 路径动态生成：
```python
EXECUTION_STEPS_PROMPT = """
你是一个智能执行规划专家。请基于用户的思考路径，生成具体的执行步骤。

用户思考路径（用户已确认的需求）:
{thinking_path}

要求:
1. 每个步骤必须对应思考路径中的已确认意图
2. 不要添加与用户需求无关的步骤
3. 只生成用户明确要求的操作
...
"""
```

**验证**: 修复后 execution 步骤为：
1. 收集技术美术基本信息
2. 分析技术美术在不同行业的应用
3. 收集游戏行业技术美术详细信息
4. 汇总技术美术职位相关信息
5. 生成技术美术职位报告

无"价格查询"、无"预算分析"。

---

### 1.5 Thinking 只跑 1 轮就收敛（已修复）

**问题**: 用户选了第一轮"技术美术"后，thinking 直接结束，没有后续澄清。

**根因**:
- `AUTO_SELECT_THRESHOLD = 0.85`，但 LLM 生成的 confidence 默认 0.95
- AI 自动选择了第 2、3 轮（用户不知情）
- `MAX_DEPTH = 3`，3 轮后直接触发收敛

**修复**:
```python
# blueclaw/core/thinking_engine.py
AUTO_SELECT_THRESHOLD = 0.92    # 0.85 → 0.92
MAX_DEPTH = 5                    # 3 → 5
```

同时重写 `THINKING_OPTIONS_PROMPT`，加入歧义识别优先：
```
1. **歧义识别优先**：如果用户输入包含缩写/多义词，首先生成澄清选项
   例如："ta"可能是"Technical Artist（技术美术）"、"Teaching Assistant"...
4. **置信度规则**：
   - 澄清类选项：confidence 0.5-0.7
   - 明确类选项：confidence 0.7-0.85
   - 绝不给 ≥0.9
```

**验证**: 修复后关闭 auto_select 时，用户手动选择 A → 第二轮弹出"技术美术具体指哪个领域？" → 第三轮弹出"游戏技术美术的具体方向？"。共 3 轮有意义的澄清。

---

### 1.6 Prompt KeyError: 'history'（已修复）

**问题**: `format_thinking_options_prompt()` 抛 `KeyError: 'history'`。

**根因**: 新模板含 `{history}` 占位符，但原实现只传了 `context`：
```python
# 原代码（错误）
return THINKING_OPTIONS_PROMPT.format(context=context)
```

**修复**:
```python
def format_thinking_options_prompt(context: str, history: list) -> str:
    import json
    return THINKING_OPTIONS_PROMPT.format(
        context=context,
        history=json.dumps(history, ensure_ascii=False, indent=2) if history else "无"
    )
```

---

## 二、测试流程

### 2.1 准备环境

```bash
# 1. 启动前端
cd blueclawv2.1/frontend && npx vite

# 2. 启动后端
cd blueclawv2.1 && python3 backend/main.py

# 3. 健康检查
curl http://127.0.0.1:8006/api/health
```

### 2.2 WebSocket 直连测试（排除前端干扰）

```python
# 脚本：/tmp/test_ws_final.py
async with websockets.connect('ws://127.0.0.1:8006/ws') as ws:
    await ws.send(json.dumps({
        'type': 'task.start',
        'payload': {
            'user_input': '去CSDN搜索ta教程',
            'auto_select': True
        }
    }))
    # 监听 120 秒，等待 thinking/execution 消息
```

### 2.3 前端 Playwright 测试

```python
# 脚本：/tmp/test_frontend_final.py
page.goto("http://127.0.0.1:5173")
page.fill("input", "去CSDN搜索ta教程")
page.click('[data-testid="submit-task"]')
# 等待 execution 节点出现（最长 120 秒）
# 截图保存
```

---

## 三、测试结果

### 3.1 WebSocket 消息时序

```
[WS] New connection → [WS] Received: task.start
  → [ThinkingEngine] Auto-selecting option A... (5轮)
  → [DEBUG] CONVERGED: path_len=5 >= MAX_DEPTH=5
  → [StateSync] broadcast: type=thinking.node_created
  → [DEBUG router] Thinking converged, auto-generating blueprint
  → [StateSync] broadcast: type=thinking.converged
  → [AutoBlueprint] Blueprint created: blueprint_eaee7900 with 5 steps
  → [StateSync] broadcast: type=execution.blueprint_loaded
  → [EXEC] Step completed: 收集技术美术基本信息
  → [StateSync] broadcast: type=execution.step_started/completed
  ...（5步全部完成）
  → [StateSync] broadcast: type=execution.completed
```

### 3.2 前端收到的消息清单

| 消息类型 | 次数 | 状态 |
|----------|------|------|
| `task.started` | 1 | ✅ |
| `thinking.node_created` | 1 | ✅ |
| `thinking.converged` | 1 | ✅ |
| `execution.blueprint_loaded` | 2 | ✅ |
| `execution.step_started` | 5 | ✅ |
| `execution.step_completed` | 5+ | ✅ |
| `execution.completed` | 1 | ✅ |

### 3.3 Execution 蓝图内容（动态生成）

```json
{
  "steps": [
    {
      "name": "收集技术美术基本信息",
      "direction": "从数据库和互联网上检索技术美术的基本信息...",
      "tool": "信息检索Skill"
    },
    {
      "name": "分析技术美术在不同行业的应用",
      "direction": "根据用户的选择，分析技术美术在游戏/影视/建筑行业的应用...",
      "tool": "网络搜索Skill"
    },
    {
      "name": "收集游戏行业技术美术详细信息",
      "direction": "深入了解游戏行业中技术美术的具体工作内容和要求...",
      "tool": "网络搜索Skill"
    },
    {
      "name": "汇总技术美术职位相关信息",
      "direction": "整合收集到的信息，形成技术美术职位的全面描述...",
      "tool": "信息汇总Skill"
    },
    {
      "name": "生成技术美术职位报告",
      "direction": "基于汇总信息，生成一份结构化的技术美术职位报告...",
      "tool": "skill-file"
    }
  ]
}
```

### 3.4 执行结果

| 步骤 | 状态 | 输出 |
|------|------|------|
| 1. 收集技术美术基本信息 | ✅ COMPLETED | TA 定义、职责、CSDN 特色资源 |
| 2. 分析技术美术在不同行业的应用 | ✅ COMPLETED | 游戏/影视/建筑行业差异 |
| 3. 收集游戏行业技术美术详细信息 | ✅ COMPLETED | 职位描述、技能、工具 |
| 4. 汇总技术美术职位相关信息 | ✅ COMPLETED | 团队结构、地点特色 |
| 5. 生成技术美术职位报告 | ✅ COMPLETED | 写入 `/tmp/task_420fd1d0_output.txt` |

---

## 四、截图证据

| 截图文件 | 内容 | 状态 |
|----------|------|------|
| `100_initial.png` | 初始输入页面 | ✅ |
| `101_with_execution.png` | Execution 蓝图渲染（35 个节点） | ✅ |
| `102_web_mode.png` | Web 模式显示 WebAdapter 浏览器截图 | ✅ |
| `02_after_thinking.png` | Thinking 多轮节点（技术美术澄清） | ✅ |
| `99_execution_final.png` | Execution 完成状态 | ✅ |

**截图目录**: `/root/.openclaw/workspace/blueclawv2.1/screenshots/csdn_test/`

---

## 五、当前状态总览

| 模块 | 状态 | 备注 |
|------|------|------|
| Thinking 多轮生成 | ✅ | 关闭 auto_select 时 3 轮澄清 |
| Auto Select 自动选择 | ✅ | 开启时 5 轮自动收敛 |
| WebSocket 推送 | ✅ | 全部消息正常到达前端 |
| Execution 蓝图生成 | ✅ | 动态生成，无硬编码 |
| Execution 逐步执行 | ✅ | 5 步全部完成 |
| WebAdapter 截图 | ✅ | Playwright 真实浏览器截图 |
| Vis-adapter 三模式 | ✅ | 画布/Web/IDE 切换正常 |
| 干预面板 | ✅ | 三选项弹出正常 |
| 拖拽功能 | ✅ | ToolDock → vis-adapter |

---

## 六、遗留问题

1. **CSDN 直达**: WebAdapter 当前通过 Bing 搜索，未直接访问 `so.csdn.net`。如需专门验证 CSDN 搜索，需在 execution 步骤的 `direction` 中明确指定 URL。
2. **前端 Checkbox**: `auto_select` 开关后端已支持，前端 InputScreen 的 checkbox UI 待实现。
3. **Debug 日志清理**: 当前代码中有大量 `flush=True` 和 DEBUG print，生产环境前需清理。

---

*报告生成时间: 2026-04-29 02:20*
*测试脚本: /tmp/test_ws_final.py, /tmp/test_frontend_final.py*
*后端日志: /tmp/backend_final_test.log*
