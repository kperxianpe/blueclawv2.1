# Blueclaw V2 前后端统一接口文档

> **版本**: v2.1-unified（基于 2026-04-22 前端代码 + 后端 message_router）
> **适用范围**: `buleclawv1-frontword` 前端 ↔ `blueclawv2/backend` 后端
> **通信方式**: WebSocket `ws://localhost:8006/ws`
> **协议说明**: 本文档同时兼容旧 API (`task.start`/`thinking.select_option`) 和 V2 API (`user_input`/`select_option`)，后端自动适配

---

## 一、接口设计原则

1. **前端驱动流程**: 前端组件触发用户操作 → 发送消息 → 后端处理 → 广播状态更新 → 前端 `RealtimeProvider` 接收并更新 Zustand Store
2. **双向消息类型**: 所有消息统一为 `{ type, payload, timestamp, message_id }`
3. **task_id 自动推断**: 前端在 WS 模式下不需要存储/传递 `task_id`，后端通过 websocket 连接关联自动推断
4. **显示优先**: 第一轮测试只验证"显示正确"，点击交互（选项选择/干预）第二轮再测

---

## 二、前端流程 ↔ 后端消息映射总表

### 2.1 流程一：初始界面 → 输入任务

| 步骤 | 前端组件 | 用户操作 | 前端发送 | 后端处理 | 后端广播/返回 | 前端接收处理 |
|------|---------|---------|---------|---------|-------------|------------|
| 1.1 | `InputScreen.tsx` | 输入任务文本 | — | — | — | `setUserInput(text)` |
| 1.2 | `InputScreen.tsx` | 点击"开始" | `task.start` / `user_input` | `_handle_task_start` | `task.started` + `thinking.node_created` | `RealtimeProvider` → `setPhase('thinking')` + 添加首节点 |

### 2.2 流程二：思考蓝图 → 选择引导方向

| 步骤 | 前端组件 | 用户操作 | 前端发送 | 后端处理 | 后端广播/返回 | 前端接收处理 |
|------|---------|---------|---------|---------|-------------|------------|
| 2.1 | `ThinkingNode.tsx` | 点击节点展开 | — (纯前端) | — | — | `setIsExpanded(true)` |
| 2.2 | `ThinkingNode.tsx` | 点击选项A/B/C | `thinking.select_option` / `select_option` | `_handle_thinking_select_option` | `thinking.option_selected` + `thinking.node_selected` | `updateThinkingNode` + 追加新节点 |
| 2.3 | `ThinkingNode.tsx` | 自定义输入 | `thinking.custom_input` / `custom_input` | `_handle_thinking_custom_input` | `thinking.custom_input_received` + `thinking.node_selected` | `updateThinkingNode` + 追加新节点 |
| 2.4 | 自动 | 第三轮选择后 | — | `_auto_generate_blueprint` | `thinking.completed` + `execution.blueprint_loaded` | `setPhase('execution')` + 加载执行步骤 |

### 2.3 流程三：执行蓝图 → 自动执行

| 步骤 | 前端组件 | 用户操作 | 前端发送 | 后端处理 | 后端广播/返回 | 前端接收处理 |
|------|---------|---------|---------|---------|-------------|------------|
| 3.1 | `ExecutionNode.tsx` | 查看蓝图 | — (纯显示) | — | `execution.blueprint_loaded` | `setExecutionSteps` + `setPhase('execution')` |
| 3.2 | 自动 | 步骤自动执行 | — | `execution_engine.start_execution` | `execution.step_started` | `updateExecutionStep(stepId, {status:'running'})` |
| 3.3 | 自动 | 步骤完成 | — | `execution_engine` | `execution.step_completed` | `updateExecutionStep(stepId, {status:'completed', result})` |
| 3.4 | 自动 | 步骤失败 | — | `execution_engine` | `execution.step_failed` | `updateExecutionStep(stepId, {status:'failed', error})` |
| 3.5 | 自动 | 全部完成 | — | `execution_engine` | `execution.completed` | `setPhase('completed')` |

### 2.4 流程四：干涉面板 → 执行节点操作

| 步骤 | 前端组件 | 用户操作 | 前端发送 | 后端处理 | 后端广播/返回 | 前端接收处理 |
|------|---------|---------|---------|---------|-------------|------------|
| 4.1 | `ExecutionNode.tsx` | 点击齿轮⚙️ | — (纯前端展开) | — | — | `setIsExpanded(true)` |
| 4.2 | `InterferencePanel.tsx` | 点击"重新执行" | `execution.intervene` (action="retry") | `_handle_execution_intervene` | `execution.intervened` | 重置步骤状态 → `executeNextStep()` |
| 4.3 | `InterferencePanel.tsx` | 点击"重新思考" | `execution.intervene` (action="replan") | `_handle_execution_intervene` | `execution.returned_to_thinking` + `thinking.node_created` | `interveneExecution()` → 回thinking阶段 |
| 4.4 | `InterferencePanel.tsx` | 点击"冻结" | `adapter.runtime.freeze` / `freeze` | `handle_adapter_runtime_freeze` | `execution.frozen` | `setIsFrozen(true)` |

### 2.5 流程五：冻结系统 → 截图分析

| 步骤 | 前端组件 | 用户操作 | 前端发送 | 后端处理 | 后端广播/返回 | 前端接收处理 |
|------|---------|---------|---------|---------|-------------|------------|
| 5.1 | `FreezeOverlay.tsx` | 点击"解释截图" | — (前端创建框) | — | — | `addBox('explain')` + `addMiniNode()` |
| 5.2 | `FreezeOverlay.tsx` | 点击"更改截图" | — (前端创建框) | — | — | `addBox('modify')` + `addMiniNode()` |
| 5.3 | `FreezeOverlay.tsx` | 小思考节点选择 | — (前端本地) | — | — | `selectMiniOption()` |
| 5.4 | `FreezeOverlay.tsx` | 点击"更改蓝图形容" | `change_description` | 待实现 | — | 更新本地描述 |
| 5.5 | `FreezeOverlay.tsx` | 点击"解冻" | `adapter.runtime.unfreeze` / `unfreeze` | `handle_adapter_runtime_unfreeze` | `execution.unfrozen` | `handleUnfreeze()` 清除状态 |

### 2.6 流程六~八：纯前端功能（无需后端接口）

| 流程 | 前端组件 | 说明 |
|------|---------|------|
| 六 | `VisualAdapter.tsx` | 标签页切换、新建/关闭标签（纯前端状态） |
| 七 | `SettingsPanel.tsx` | 画布参数调节（纯前端 Zustand store） |
| 八 | `ToolDock.tsx` | 工具拖拽、搜索过滤（纯前端） |

---

## 三、消息格式详细定义

### 3.1 客户端 → 服务端（Client → Server）

#### `task.start` / `user_input` — 启动任务

```typescript
// 旧 API（前端当前使用）
{ type: "task.start", payload: { user_input: string } }

// V2 API（兼容）
{ type: "user_input", payload: { input: string } }
```

#### `thinking.select_option` / `select_option` — 选择思考选项

```typescript
// 旧 API（前端当前使用，task_id 可为空由后端推断）
{ type: "thinking.select_option", payload: { task_id?: "", current_node_id: string, option_id: string } }

// V2 API（兼容）
{ type: "select_option", payload: { nodeId: string, optionId: string } }
```

#### `thinking.custom_input` / `custom_input` — 自定义输入

```typescript
// 旧 API
{ type: "thinking.custom_input", payload: { task_id?: "", current_node_id: string, custom_input: string } }

// V2 API
{ type: "custom_input", payload: { nodeId: string, input: string } }
```

#### `execution.intervene` — 执行干预

```typescript
{ type: "execution.intervene", payload: {
    task_id?: string,       // 可为空，后端推断
    blueprint_id?: string,  // 可为空，后端通过 task_id 查找
    step_id: string,
    action: "replan" | "skip" | "retry" | "modify",
    custom_input?: string   // replan 时可选
}}
```

#### `adapter.runtime.freeze` / `freeze` — 冻结执行

```typescript
// 已有 handler
{ type: "adapter.runtime.freeze", payload: { blueprint_id: string, step_id: string } }

// V2 简写（待添加 handler）
{ type: "freeze", payload: { stepId: string } }
```

#### `adapter.runtime.unfreeze` / `unfreeze` — 解除冻结

```typescript
// 已有 handler
{ type: "adapter.runtime.unfreeze", payload: { blueprint_id: string } }

// V2 简写（待添加 handler）
{ type: "unfreeze", payload: {} }
```

### 3.2 服务端 → 客户端（Server → Client）

#### `task.started` — 任务已启动

```typescript
{
  type: "task.started",
  payload: {
    task_id: string,
    user_input: string
  }
}
```

#### `thinking.node_created` / `thinking.node_selected` — 新思考节点

```typescript
{
  type: "thinking.node_created",      // 首节点
  // type: "thinking.node_selected",  // 后续节点
  payload: {
    node: {
      id: string,
      question: string,
      options: [
        { id: string, label: string, description: string, confidence: number, is_default?: boolean }
      ],
      allow_custom: boolean
    },
    allow_custom: boolean,
    previous_node_id: string | null
  }
}
```

#### `thinking.option_selected` — 选项已选择确认

```typescript
{
  type: "thinking.option_selected",
  payload: {
    task_id: string,
    option_id: string,
    current_node_id: string,
    has_more_options: boolean,
    final_path?: any[]
  }
}
```

#### `thinking.completed` — 思考阶段完成

```typescript
{
  type: "thinking.completed",
  payload: {
    final_path: any[]
  }
}
```

#### `execution.blueprint_loaded` — 执行蓝图已加载

```typescript
{
  type: "execution.blueprint_loaded",
  payload: {
    blueprint: {
      id: string,
      steps: ExecutionStep[]
    }
  }
}
// ExecutionStep 字段参见前端 types/index.ts
```

#### `execution.step_started` — 步骤开始执行

```typescript
{
  type: "execution.step_started",
  payload: {
    step_id: string,
    id: string,          // 同 step_id
    name: string,
    status: "running",
    start_time?: string,
    tool?: string
  }
}
```

#### `execution.step_completed` — 步骤执行完成

```typescript
{
  type: "execution.step_completed",
  payload: {
    step_id: string,
    id: string,
    name: string,
    status: "completed",
    result?: string,
    duration_ms?: number
  }
}
```

#### `execution.step_failed` — 步骤执行失败

```typescript
{
  type: "execution.step_failed",
  payload: {
    step_id: string,
    status: "failed",
    error: string,
    can_retry: boolean,
    error_type?: string,
    stack_trace?: string
  }
}
```

#### `execution.completed` — 全部执行完成

```typescript
{
  type: "execution.completed",
  payload: {
    success: boolean,
    summary: string,
    completed_steps: number,
    total_steps: number,
    execution_time: number
  }
}
```

#### `execution.intervention_needed` — 需要用户干预

```typescript
{
  type: "execution.intervention_needed",
  payload: {
    step_id: string,
    step_name: string,
    reason: string,
    suggested_actions: [
      { id: "replan", label: "重新规划", description: "..." },
      { id: "skip", label: "跳过此步", description: "..." },
      { id: "retry", label: "重试", description: "..." },
      { id: "custom", label: "自定义方案", description: "..." }
    ]
  }
}
```

#### `execution.returned_to_thinking` — 执行返回思考阶段

```typescript
{
  type: "execution.returned_to_thinking",
  payload: {
    archived_step_ids: string[]
  }
}
```

---

## 四、状态流转图

```
┌─────────┐   task.start      ┌───────────┐   select_option (x3)   ┌───────────┐
│  input  │ ─────────────────►│ thinking  │ ──────────────────────►│ execution │
└─────────┘                   └───────────┘                        └───────────┘
     ▲                              │                                    │
     │                              │ intervene (replan)                   │ intervene (retry/skip)
     │                              ▼                                    ▼
     │                       ┌───────────┐                        ┌───────────┐
     │                       │intervention│                      │intervention│
     │                       └───────────┘                        └───────────┘
     │                                                                    │
     │                              freeze                                │
     │                              ▼                                     │
     │                       ┌───────────┐                                │
     └───────────────────────│  freeze   │◄───────────────────────────────┘
         reset/complete      └───────────┘        unfreeze
```

---

## 五、前后端责任边界

### 5.1 前端负责（纯 UI/交互）

| 功能 | 组件 | 说明 |
|------|------|------|
| 节点展开/折叠 | `ThinkingNode.tsx` / `ExecutionNode.tsx` | `isExpanded` 本地 state |
| 选项高亮/选中样式 | `ThinkingNode.tsx` | 根据 `node.status` 渲染 |
| 工具栏搜索过滤 | `ToolDock.tsx` | 纯前端字符串匹配 |
| 标签页切换 | `VisualAdapter.tsx` | `activeTabId` 本地 state |
| 设置面板参数 | `SettingsPanel.tsx` | `canvasConfig` Zustand state |
| 截图框拖拽 | `FreezeOverlay.tsx` | 鼠标事件本地处理 |
| 小思考蓝图 | `FreezeOverlay.tsx` | 纯前端本地 state |

### 5.2 后端负责（数据/逻辑）

| 功能 | 模块 | 说明 |
|------|------|------|
| 思考节点生成 | `thinking_engine.py` | LLM 调用生成问题+选项 |
| 思考路径管理 | `thinking_engine.py` | `task_nodes` / `nodes` 存储 |
| 执行蓝图生成 | `execution_engine.py` | 根据思考收敛结果生成步骤 |
| 步骤执行调度 | `execution_engine.py` | 依赖解析、并行/串行执行 |
| 状态广播 | `state_sync.py` | WebSocket 推送到所有连接 |
| 任务检查点 | `checkpoint_manager.py` | 任务状态持久化 |

### 5.3 前后端协作（消息交互）

| 功能 | 前端责任 | 后端责任 |
|------|---------|---------|
| 任务启动 | 发送 `task.start` | 创建 task，生成首节点，广播 |
| 选项选择 | 发送 `thinking.select_option` | 更新路径，生成下一节点/收敛 |
| 执行干预 | 发送 `execution.intervene` | 执行干预逻辑，广播新状态 |
| 冻结/解冻 | 发送 `adapter.runtime.freeze/unfreeze` | 标记冻结状态，广播 |

---

## 六、待实现/待补充接口

### 6.1 后端待补充

| # | 缺失项 | 优先级 | 说明 |
|---|--------|--------|------|
| 1 | `change_description` handler | 低 | 冻结时更改蓝图形容 |
| 2 | `add_screenshot_box` handler | 低 | 向后端发送截图框信息 |
| 3 | `select_mini_option` handler | 低 | 小思考蓝图选项选择 |
| 4 | `execution.frozen` 广播消息 | 中 | 冻结状态变更通知前端 |
| 5 | `execution.unfrozen` 广播消息 | 中 | 解冻状态变更通知前端 |

### 6.2 前端待补充

| # | 缺失项 | 优先级 | 说明 |
|---|--------|--------|------|
| 1 | `InterferencePanel` 发送 `execution.intervene` | 中 | 当前仅本地状态，未发 WS |
| 2 | `FreezeOverlay` 发送 `adapter.runtime.freeze/unfreeze` | 中 | 当前仅本地状态 |
| 3 | 冻结时向后端发送截图 | 低 | 需要截图捕获实现 |

---

## 七、测试策略（按轮次）

### 第一轮：显示验证（不点击）

1. 启动后端 + 前端
2. 输入任务 → 验证 thinking 阶段首节点**显示**
3. 等待自动流程或 Mock → 验证 execution 阶段步骤**显示**
4. 验证画布布局、节点样式、连线正确

### 第二轮：核心交互（点击选择）

1. 展开思考节点 → 选择选项 → 验证下一节点出现
2. 完成三轮 → 验证自动转入 execution
3. 验证执行步骤状态变化

### 第三轮：高级功能（干预/冻结）

1. 执行节点齿轮按钮 → 验证干涉面板显示
2. 冻结 → 验证 FreezeOverlay 显示
3. 截图框 → 小思考蓝图 → 解冻

---

*文档版本: 2026-04-04*
*前端版本: buleclawv1-frontword v2.1*
*后端版本: blueclawv2/backend v2.5*
