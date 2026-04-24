# Blueclaw v2 功能手册

本文档列出 Blueclaw v2 的核心功能、入口类/函数及调用示例。

---

## 1. ThinkingEngine

**一句话描述**：管理多轮澄清流程，生成选项树并收敛为最终思考路径。

**入口**：`blueclaw.core.thinking_engine.ThinkingEngine`

**调用示例**：
```python
from blueclaw.core.thinking_engine import thinking_engine

# 启动思考流程
result = await thinking_engine.start_thinking(
    task_id="task_001",
    user_input="帮我规划一个北京4天旅游攻略"
)

# 选择选项
node = await thinking_engine.select_option(
    task_id="task_001",
    node_id="node_001",
    option_id="opt_A"
)

# 获取最终路径
final_path = thinking_engine.get_final_path("task_001")
```

**参数与返回值**：
- `start_thinking(task_id, user_input)` → `ThinkingNode`（首节点）
- `select_option(task_id, node_id, option_id)` → `ThinkingNode`（下一节点或收敛节点）
- `get_final_path(task_id)` → `List[dict]`（按顺序的选择路径）

---

## 2. ExecutionEngine

**一句话描述**：从思考路径生成执行蓝图（DAG），并按依赖拓扑执行步骤。

**入口**：`blueclaw.core.execution_engine.ExecutionEngine`

**调用示例**：
```python
from blueclaw.core.execution_engine import execution_engine
from blueclaw.core.state_sync import state_sync

# 生成蓝图
blueprint = await execution_engine.create_blueprint(
    task_id="task_001",
    thinking_path=final_path
)

# 开始执行
await execution_engine.start_execution(blueprint.id)

# 暂停 / 恢复
await execution_engine.pause_execution(blueprint.id)
await execution_engine.resume_execution(blueprint.id)

# 取消
await execution_engine.cancel_execution(blueprint.id)
```

**参数与返回值**：
- `create_blueprint(task_id, thinking_path)` → `ExecutionBlueprint`
- `start_execution(blueprint_id)` → `None`
- `pause_execution(blueprint_id)` / `resume_execution(blueprint_id)` / `cancel_execution(blueprint_id)` → `None`

---

## 3. LLMClient

**一句话描述**：统一封装 Kimi / OpenAI 的异步 LLM 调用客户端，支持连接池复用和原生取消。

**入口**：`blueclaw.llm.client.LLMClient`

**调用示例**：
```python
from blueclaw.llm.client import LLMClient, Message

client = LLMClient()

response = await client.chat_completion(
    messages=[
        Message(role="system", content="You are a task planner."),
        Message(role="user", content="请列出3个步骤")
    ],
    temperature=0.7,
    max_tokens=2000
)

print(response.content)
```

**参数与返回值**：
- `chat_completion(messages, temperature=0.7, max_tokens=2000)` → `LLMResponse`
  - `messages`: `List[Message]`
  - `temperature`: `float`
  - `max_tokens`: `int`
- 返回值 `LLMResponse` 字段：`content`, `model`, `usage`, `finish_reason`

**环境变量**：
- `KIMI_API_KEY` / `OPENAI_API_KEY`：自动识别 provider
- `USE_SYNC_LLM=1`：紧急回退到同步 `urllib` 路径

---

## 4. MessageRouter

**一句话描述**：WebSocket 消息路由器，将前端消息分发到 Thinking / Execution / Vis / Tool / Adapter 等处理器。

**入口**：`backend.websocket.message_router.MessageRouter`

**调用示例**：
```python
from backend.websocket.message_router import MessageRouter

router = MessageRouter()

# 通常在 WebSocket server 中调用
response = await router.handle_message(
    websocket=ws,
    message={"type": "task.start", "payload": {"user_input": "..."}},
    server=websocket_server
)
```

**核心消息类型**：
- `task.start`
- `thinking.select_option` / `thinking.custom_input` / `thinking.confirm_execution`
- `execution.start` / `execution.pause` / `execution.resume` / `execution.intervene` / `execution.cancel`
- `vis.preview` / `vis.action`
- `tools.list` / `tools.inspect`
- `adapter.list` / `adapter.execute`

---

## 5. CancellationToken

**一句话描述**：可级联传播的可取消令牌，用于在任务树中实现从顶到底的取消通知。

**入口**：`blueclaw.core.execution_engine.CancellationToken`

**调用示例**：
```python
from blueclaw.core.execution_engine import CancellationToken

parent = CancellationToken(owner_id="task_001")
child = CancellationToken(owner_id="blueprint_001")
parent.add_child(child)

# 取消父节点会自动取消子节点
parent.cancel()
assert child.is_cancelled
```

**主要方法**：
- `cancel()`：取消自身并递归取消所有子 token
- `is_cancelled`（property）：`bool`
- `validate()`：若已取消则抛出 `asyncio.CancelledError`
- `add_child(token)`：添加子 token

---

## 6. StateSyncManager

**一句话描述**：统一的状态同步广播器，将后端事件实时推送到前端 WebSocket 连接。

**入口**：`blueclaw.core.state_sync.StateSyncManager`

**调用示例**：
```python
from blueclaw.core.state_sync import state_sync

# 通常在引擎内部调用，无需手动触发
await state_sync.push_thinking_node_created(task_id, node)
await state_sync.push_execution_blueprint_loaded(task_id, blueprint)
await state_sync.push_execution_step_started(task_id, step)
await state_sync.push_execution_step_completed(task_id, step)
await state_sync.push_execution_step_failed(task_id, step, error_type, stack_trace)
```

**核心方法**：
- `push_thinking_node_created(task_id, node)`
- `push_thinking_completed(task_id, final_path)`
- `push_execution_blueprint_loaded(task_id, blueprint)`
- `push_execution_step_started(task_id, step)`
- `push_execution_step_completed(task_id, step)`
- `push_execution_step_failed(task_id, step, error_type, stack_trace)`
- `push_intervention_needed(task_id, reason, context)`

---

## 7. ToolRegistry

**一句话描述**：工具注册中心，管理可用工具（搜索、文件操作、浏览器等）的元数据与执行入口。

**入口**：`blueclaw.skills.registry.ToolRegistry`（若存在）或 `backend.tools`

**说明**：工具系统在第 20.5 周引入，支持在 Blueprint 生成时自动绑定工具（如步骤名称含"搜索"则绑定 `skill-search`），并在执行阶段调用。

**自动绑定规则**（在 `ExecutionEngine.create_blueprint` 中）：
- 名称含 `价格/预算/费用/查询/搜索/查` → `skill-search`
- 名称含 `文档/报告/攻略/写入/保存/生成文件/写文件` → `skill-file`
- 名称含 `读取/获取文件/读文件` → `skill-file`

---

## 8. ReplanEngine

**一句话描述**：基于失败步骤或用户干预上下文，重新生成执行蓝图。

**入口**：`blueclaw.core.replan_engine.ReplanEngine`

**调用示例**：
```python
from blueclaw.core.replan_engine import replan_engine
from blueclaw.core.execution_engine import ExecutionStep

new_blueprint = replan_engine.replan(
    all_steps=old_blueprint.steps,
    failed_step=failed_step,
    user_feedback="希望能加入更多历史文化景点"
)
```

**参数**：
- `all_steps`: `List[ExecutionStep]`（原蓝图所有步骤）
- `failed_step`: `ExecutionStep`（触发 replan 的步骤）
- `user_feedback`: `str`（用户反馈或干预原因）

**返回值**：`ReplanResult`（包含新步骤列表和变更说明）

---

## 9. 错误治理（StepExecutionError）

**一句话描述**：对执行阶段错误进行分类，区分可恢复与不可恢复，并联动干预机制。

**入口**：`blueclaw.core.execution_engine.StepExecutionError`

**调用示例**：
```python
from blueclaw.core.execution_engine import StepExecutionError

# 在引擎内部自动抛出
try:
    await execution_engine._execute_step(blueprint, step, token)
except StepExecutionError as e:
    if e.recoverable:
        # 自动重试（最多 2 次）
        pass
    else:
        # 推送真实失败，累计 ≥2 次触发干预
        pass
```

**字段**：
- `error_type`: `str`（如 `timeout`, `connection`, `llm_error`, `cancelled`）
- `recoverable`: `bool`
- `context`: `dict`（包含原始异常信息、消息等）

**联动机制**：同一 Blueprint 累计失败 ≥2 步时，自动调用 `_notify_intervention_needed`。

---

## 附录：环境变量速查

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `KIMI_API_KEY` | Kimi API 密钥 | - |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `USE_SYNC_LLM` | 强制使用同步 LLM 回退 | `0` |
| `PYTHONPATH` | 项目根目录路径 | 由启动脚本自动注入 |
