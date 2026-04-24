# Blueclaw V2 统一接口规范文档

> **版本**: v2.1.0-unified  
> **生效日期**: 2026-04-23  
> **状态**: 运行时规范（已验证 + 代码实现）  
> **前置阅读**: 本文档取代 `api_specification.md` 和 `API_INTERFACE_V2.md`，为唯一权威规范  
> **WS 路径**: `ws://127.0.0.1:8006/ws`

---

## 一、通信协议

| 项目 | 规范 |
|------|------|
| **协议** | WebSocket (RFC 6455) |
| **传输层** | TCP |
| **地址** | `ws://127.0.0.1:8006/ws` |
| **编码** | JSON (UTF-8) |
| **心跳** | 客户端库自动处理（指数退避重连） |
| **连接模式** | 持久连接，断线后自动重连 |

> **注意**: 使用 `127.0.0.1` 而非 `localhost`，避免 IPv6 解析问题。

---

## 二、消息格式

所有消息统一使用以下结构：

```json
{
  "type": "domain.action",
  "payload": { },
  "message_id": "uuid-v4-string",
  "timestamp": 1713861600000
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | **是** | 消息类型，点号分隔（`domain.action`） |
| `payload` | object | **是** | 消息载荷 |
| `message_id` | string | 否 | UUID v4，用于去重 |
| `timestamp` | number | 否 | Unix 毫秒时间戳 |

### 2.1 命名规范

| 维度 | 规范 | 示例 |
|------|------|------|
| 消息类型 | 点号分隔，小写 | `thinking.node_created` |
| 字段名 | 下划线分隔，小写 | `current_node_id` |
| 枚举值 | 小写 | `"pending"`, `"running"`, `"completed"` |

---

## 三、数据模型

### 3.1 ThinkingNode（思考节点）

```typescript
interface ThinkingNode {
  id: string;                    // 格式: "thinking_xxxxxxxx"
  question: string;              // 向用户提出的问题
  options: ThinkingOption[];     // 选项列表
  status: 'pending' | 'selected' | 'resolved';
  selectedOption?: string;       // 已选选项 ID
  customInput?: string;          // 自定义输入（用户输入自定义内容时）
  depth: number;                 // 思考深度（0-based）
  allowCustom: boolean;          // 是否允许自定义输入（默认 true）
}

interface ThinkingOption {
  id: string;                    // "A" | "B" | "C" | "D" | "custom"
  label: string;                 // 选项标题
  description: string;           // 选项详细描述
  confidence: number;            // LLM 置信度 0.0 ~ 1.0
  recommended: boolean;          // 是否为高置信度推荐
}
```

### 3.2 ExecutionStep（执行步骤）

```typescript
interface ExecutionStep {
  id: string;                    // 格式: "step_X" 或 "branch_XX"
  name: string;                  // 步骤名称
  description: string;           // 步骤描述
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  dependencies: string[];        // 前置步骤 ID 列表
  result?: any;                  // 执行结果（任意结构）
  error?: string;                // 错误信息
  position?: { x: number; y: number };  // 画布位置（前端自动计算）
  
  // 视觉属性
  isMainPath: boolean;           // true=主路径
  isConvergence?: boolean;       // true=汇合节点
  convergenceType?: 'parallel' | 'sequential';
  needsIntervention?: boolean;   // 是否需要用户干预
  isArchived?: boolean;          // 干预后是否归档
}
```

### 3.3 AppPhase（应用阶段）

```typescript
type AppPhase = 'input' | 'thinking' | 'execution' | 'completed';
```

| 阶段 | 说明 | 触发条件 |
|------|------|---------|
| `input` | 初始状态，等待用户输入 | 页面加载完成 |
| `thinking` | 生成思考蓝图，用户选择选项 | 收到 `task.started` |
| `execution` | 执行生成的执行蓝图 | 收到 `execution.blueprint_loaded` |
| `completed` | 所有步骤执行完成 | 收到 `execution.completed` |

> **注意**: 阶段切换不由独立的 `phase_change` 事件驱动，而是由具体业务事件隐含推断。

---

## 四、前端 → 后端接口（Client → Server）

### 4.1 任务启动

```json
{
  "type": "user_input",
  "payload": {
    "user_input": "Plan a weekend trip to Hangzhou",
    "task_id": ""
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_input` | string | **是** | 用户自然语言输入 |
| `task_id` | string | 否 | 可为空（后端自动推断） |

**后端处理**: 创建任务 → 生成根思考节点 → 推送 `thinking.node_created` + `task.started`

**状态**: ✅ 已验证

---

### 4.2 选择思考选项

```json
{
  "type": "select_option",
  "payload": {
    "task_id": "",
    "current_node_id": "thinking_879ebf59",
    "option_id": "A"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 否 | 可为空（后端自动推断） |
| `current_node_id` | string | **是** | 当前思考节点 ID |
| `option_id` | string | **是** | 选项 ID（如 "A", "B", "custom"） |

**后端处理**: 标记节点选择 → 检查深度 → 生成子节点或收敛 → 推送 `thinking.option_selected` + `thinking.node_selected`（或 `thinking.completed` + `thinking.converged`）

**状态**: ✅ 已验证

---

### 4.3 自定义输入

```json
{
  "type": "custom_input",
  "payload": {
    "task_id": "",
    "current_node_id": "thinking_879ebf59",
    "custom_input": "我想去西湖和灵隐寺"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 否 | 可为空（后端自动推断） |
| `current_node_id` | string | **是** | 当前思考节点 ID |
| `custom_input` | string | **是** | 用户自定义输入文本 |

**后端处理**: 创建 custom option → 调用 `select_option_impl`

**状态**: ✅ 已验证

---

### 4.4 请求冻结

```json
{
  "type": "freeze_request",
  "payload": {
    "task_id": "task_abc123",
    "blueprint_id": "bp_xxx",
    "step_id": "step_3",
    "reason": "需要用户确认预算范围"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | **是** | 任务 ID |
| `blueprint_id` | string | **是** | 蓝图 ID |
| `step_id` | string | **是** | 当前步骤 ID |
| `reason` | string | 否 | 冻结原因 |

**后端处理**: 暂停执行 → 截图 → 推送 `freeze.confirmed`

**状态**: ⬜ 新注册，待联调

---

### 4.5 提交标注/解除冻结

```json
{
  "type": "submit_annotation",
  "payload": {
    "task_id": "task_abc123",
    "blueprint_id": "bp_xxx",
    "action": "retry",
    "annotation_id": "ann_001"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | **是** | 任务 ID |
| `blueprint_id` | string | **是** | 蓝图 ID |
| `action` | string | **是** | `"retry"` / `"replan"` / `"skip"` |
| `annotation_id` | string | 否 | 标注 ID |

**后端处理**: 根据 action 执行重试/重新规划/跳过 → 推送 `status_update`

**状态**: ⬜ 新注册，待联调

---

### 4.6 重试步骤

```json
{
  "type": "retry_step",
  "payload": {
    "task_id": "task_abc123",
    "blueprint_id": "bp_xxx",
    "step_id": "step_3",
    "reason": "API 超时"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | **是** | 任务 ID |
| `blueprint_id` | string | **是** | 蓝图 ID |
| `step_id` | string | **是** | 要重试的步骤 ID |
| `reason` | string | 否 | 重试原因 |

**后端处理**: 重置步骤状态 → 重新执行 → 推送 `execution.step_started`

**状态**: ⬜ 新注册，待联调

---

### 4.7 请求重新规划

```json
{
  "type": "request_replan",
  "payload": {
    "task_id": "task_abc123",
    "blueprint_id": "bp_xxx",
    "step_id": "step_3",
    "reason": "交通查询持续失败"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | **是** | 任务 ID |
| `blueprint_id` | string | **是** | 蓝图 ID |
| `step_id` | string | **是** | 当前步骤 ID |
| `reason` | string | 否 | 重新规划原因 |

**后端处理**: 生成新规划 → 推送 `replan.result`

**状态**: ⬜ 新注册，待联调

---

### 4.8 确认重新规划

```json
{
  "type": "confirm_replan",
  "payload": {
    "task_id": "task_abc123",
    "blueprint_id": "bp_xxx",
    "accept": true
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | **是** | 任务 ID |
| `blueprint_id` | string | **是** | 蓝图 ID |
| `accept` | boolean | **是** | true=接受新规划，false=拒绝 |

**后端处理**: 接受 → 切换到 running；拒绝 → 保持 paused → 推送 `replan.confirmed`

**状态**: ⬜ 新注册，待联调

---

### 4.9 视觉系统接口

```json
{
  "type": "vis.preview",
  "payload": {
    "task_id": "task_abc123",
    "task_description": "搜索杭州酒店"
  }
}

{
  "type": "vis.user_selection",
  "payload": {
    "task_id": "task_abc123",
    "screenshot_id": "ss_001",
    "selection": {"x": 100, "y": 200, "width": 300, "height": 150}
  }
}

{
  "type": "vis.confirm",
  "payload": {
    "task_id": "task_abc123",
    "screenshot_id": "ss_001",
    "action": "click",
    "x": 150,
    "y": 250
  }
}

{
  "type": "vis.action",
  "payload": {
    "task_id": "task_abc123",
    "action_def": {"action": "click", "target": "搜索按钮"}
  }
}
```

**状态**: ✅ 代码已实现，待文档化验证

---

## 五、后端 → 前端接口（Server → Client）

### 5.1 任务启动确认

```json
{
  "type": "task.started",
  "payload": {
    "task_id": "task_abc123",
    "user_input": "Plan a weekend trip to Hangzhou"
  }
}
```

**触发时机**: 后端成功创建任务  
**前端动作**: 设置 user_input，切换 phase 到 `thinking`  
**状态**: ✅ 已验证

---

### 5.2 思考节点创建（根节点）

```json
{
  "type": "thinking.node_created",
  "payload": {
    "node": {
      "id": "thinking_879ebf59",
      "question": "您计划周末去杭州旅行，以下是几种不同的旅行方案",
      "options": [
        {
          "id": "A",
          "label": "文化探索之旅",
          "description": "探索杭州的历史文化遗产...",
          "confidence": 0.82,
          "recommended": false
        }
      ],
      "status": "pending",
      "depth": 0,
      "allow_custom": true
    }
  }
}
```

**触发时机**: 生成根思考节点  
**前端动作**: 添加节点，自动选中并展开  
**状态**: ✅ 已验证

---

### 5.3 思考节点选择（非根节点）

```json
{
  "type": "thinking.node_selected",
  "payload": {
    "node": { ... }
  }
}
```

**触发时机**: 用户选择后生成子节点  
**前端动作**: 追加到节点列表  
**状态**: ✅ 已验证

---

### 5.4 选项已选择确认

```json
{
  "type": "thinking.option_selected",
  "payload": {
    "current_node_id": "thinking_879ebf59",
    "option_id": "A",
    "selected_label": "文化探索之旅"
  }
}
```

**触发时机**: 选项被成功处理  
**前端动作**: 更新节点状态为 `selected`  
**状态**: ✅ 已验证

---

### 5.5 思考完成

```json
{
  "type": "thinking.completed",
  "payload": {
    "task_id": "task_abc123",
    "final_path": ["thinking_879ebf59"],
    "summary": "用户选择了文化探索之旅"
  }
}
```

**触发时机**: 思考链达到完成条件  
**前端动作**: 日志记录，等待收敛  
**状态**: ✅ 已验证

---

### 5.6 思考收敛

```json
{
  "type": "thinking.converged",
  "payload": {
    "task_id": "task_abc123",
    "convergence_reason": "max_depth_reached",
    "final_path": ["thinking_879ebf59"],
    "auto_transition": true
  }
}
```

**触发时机**: 思考深度达到 MAX_DEPTH 或所有分支已解决  
**前端动作**: 标记思考结束，准备接收蓝图  
**状态**: ✅ 已验证

---

### 5.7 执行蓝图加载

```json
{
  "type": "execution.blueprint_loaded",
  "payload": {
    "blueprint": {
      "id": "bp_001",
      "steps": [
        {
          "id": "step_1",
          "name": "信息检索",
          "description": "检索杭州旅游相关信息",
          "status": "pending",
          "dependencies": [],
          "is_main_path": true
        }
      ]
    }
  }
}
```

**触发时机**: 思考收敛后生成蓝图  
**前端动作**: 加载步骤，切换 phase 到 `execution`  
**状态**: ✅ 已验证

---

### 5.8 执行步骤开始

```json
{
  "type": "execution.step_started",
  "payload": {
    "step_id": "step_1",
    "id": "step_1",
    "name": "信息检索",
    "status": "running",
    "tool": "Skill"
  }
}
```

**触发时机**: 某步骤开始执行  
**前端动作**: 更新步骤状态为 `running`  
**状态**: ✅ 已验证

---

### 5.9 执行步骤完成

```json
{
  "type": "execution.step_completed",
  "payload": {
    "step_id": "step_1",
    "id": "step_1",
    "name": "信息检索",
    "status": "completed",
    "result": { "attractions": ["西湖", "灵隐寺"] },
    "duration_ms": 5200
  }
}
```

**触发时机**: 步骤成功执行完毕  
**前端动作**: 更新状态为 `completed`，存储 result  
**状态**: ✅ 已验证

---

### 5.10 执行步骤失败

```json
{
  "type": "execution.step_failed",
  "payload": {
    "step_id": "step_2",
    "status": "failed",
    "error": "交通查询 API 超时",
    "can_retry": true,
    "error_type": "timeout"
  }
}
```

**触发时机**: 步骤执行失败  
**前端动作**: 更新状态为 `failed`，显示错误  
**状态**: ⚠️ 代码已实现，未验证

---

### 5.11 需要人工干预

```json
{
  "type": "execution.intervention_needed",
  "payload": {
    "step_id": "step_3",
    "step_name": "预算分析",
    "reason": "需要用户确认预算范围",
    "suggested_actions": [
      {"id": "replan", "label": "重新规划", "description": "更换策略重新执行"},
      {"id": "skip", "label": "跳过此步", "description": "继续后续步骤"},
      {"id": "retry", "label": "重试", "description": "再次尝试执行"},
      {"id": "custom", "label": "自定义方案", "description": "输入您的偏好"}
    ]
  }
}
```

**触发时机**: 执行步骤需要用户输入/确认  
**前端动作**: 显示干预面板  
**状态**: ⚠️ 代码已实现，未验证

---

### 5.12 返回思考阶段

```json
{
  "type": "execution.returned_to_thinking",
  "payload": {
    "task_id": "task_abc123",
    "archived_step_ids": ["step_3", "step_4"],
    "reason": "执行失败，需要重新思考"
  }
}
```

**触发时机**: 执行严重失败，回退到思考  
**前端动作**: 归档步骤，切换 phase 到 `thinking`  
**状态**: ⚠️ 代码已实现，未验证

---

### 5.13 执行完成

```json
{
  "type": "execution.completed",
  "payload": {
    "success": true,
    "summary": "任务执行完成",
    "completed_steps": 6,
    "total_steps": 6,
    "execution_time": 45.2,
    "can_save": true
  }
}
```

**触发时机**: 所有步骤执行完成  
**前端动作**: 切换 phase 到 `completed`  
**状态**: ⚠️ 代码已实现，未验证

---

### 5.14 执行暂停/恢复

```json
{
  "type": "execution.paused",
  "payload": {
    "blueprint_id": "bp_001"
  }
}

{
  "type": "execution.resumed",
  "payload": {
    "blueprint_id": "bp_001"
  }
}
```

**状态**: ⚠️ 代码已实现，未验证

---

### 5.15 重新规划结果

```json
{
  "type": "execution.replanned",
  "payload": {
    "from_step_id": "step_3",
    "abandoned_steps": ["step_3", "step_4"],
    "new_steps": [
      {"id": "step_3_new", "name": "备选交通查询", ...}
    ]
  }
}
```

**状态**: ⚠️ 代码已实现，未验证

---

### 5.16 截图推送

```json
{
  "type": "screenshot",
  "payload": {
    "adapterId": "task_abc123",
    "stepId": "step_2",
    "image": "/9j/4AAQSkZJRgABAQ...",
    "timestamp": 1713861600000
  }
}
```

**触发时机**: Adapter 执行 Web 步骤后截图  
**前端动作**: 在 WebView 中显示截图  
**状态**: ⬜ 新实现，待联调验证

---

### 5.17 状态更新

```json
{
  "type": "status_update",
  "payload": {
    "adapterId": "task_abc123",
    "state": "running",
    "currentStep": {"index": 2, "status": "running"},
    "requiresIntervention": false
  }
}
```

**触发时机**: 执行状态变更  
**前端动作**: 更新状态栏/进度指示  
**状态**: ⬜ 新实现，待联调验证

---

### 5.18 冻结确认

```json
{
  "type": "freeze.confirmed",
  "payload": {
    "adapterId": "task_abc123",
    "stepId": "step_3",
    "screenshot": "/9j/4AAQSkZJRgABAQ...",
    "freezeToken": "freeze_task_abc123_1713861600"
  }
}
```

**触发时机**: 后端确认冻结请求  
**前端动作**: 显示 FreezeOverlay  
**状态**: ⬜ 新实现，待联调验证

---

### 5.19 重新规划确认

```json
{
  "type": "replan.result",
  "payload": {
    "adapterId": "task_abc123",
    "accepted": true,
    "newSteps": [...],
    "reason": "新规划已生成"
  }
}
```

**触发时机**: 重新规划结果  
**前端动作**: 显示新规划，等待用户确认  
**状态**: ⬜ 新实现，待联调验证

---

### 5.20 错误消息

```json
{
  "type": "error",
  "payload": {
    "message": "Unknown message type: invalid_type",
    "code": "UNKNOWN_MESSAGE_TYPE",
    "step_id": "step_2"
  }
}
```

**触发时机**: 消息路由失败、handler 异常  
**前端动作**: 控制台输出，可显示 Toast  
**状态**: ⚠️ 代码已实现，未验证

---

## 六、视觉系统接口（Vis-Adapter）

### 6.1 后端 → 前端

| 消息类型 | 说明 | 状态 |
|---------|------|------|
| `vis.preview` | 视觉预览（截图 + 元素分析） | ✅ 代码有 |
| `vis.action_executed` | 视觉动作执行结果 | ✅ 代码有 |
| `vis.skipped` | 视觉步骤已跳过 | ✅ 代码有 |
| `vis.batch_executed` | 批量视觉操作结果 | ✅ 代码有 |
| `vis.action_result` | 单个视觉动作结果 | ✅ 代码有 |

### 6.2 前端 → 后端

| 消息类型 | 说明 | 状态 |
|---------|------|------|
| `vis.preview` | 请求视觉预览 | ✅ 代码有 |
| `vis.user_selection` | 用户框选区域 | ✅ 代码有 |
| `vis.confirm` | 确认视觉操作 | ✅ 代码有 |
| `vis.skip` | 跳过视觉步骤 | ✅ 代码有 |
| `vis.batch_confirm` | 批量确认 | ✅ 代码有 |
| `vis.action` | 执行视觉动作 | ✅ 代码有 |

---

## 七、错误码规范

| 错误码 | 含义 | 触发场景 |
|--------|------|---------|
| `UNKNOWN_MESSAGE_TYPE` | 未知消息类型 | 前端发送了后端未注册的消息 type |
| `INVALID_PAYLOAD` | 载荷格式错误 | payload 缺少必要字段 |
| `TASK_NOT_FOUND` | 任务不存在 | 使用了无效的 task_id |
| `NODE_NOT_FOUND` | 节点不存在 | 使用了无效的 node_id |
| `OPTION_NOT_FOUND` | 选项不存在 | 使用了无效的 option_id |
| `MAX_DEPTH_REACHED` | 已达到最大深度 | 思考链无法继续延伸 |
| `LLM_API_ERROR` | LLM 调用失败 | KIMI API 返回错误 |
| `EXECUTION_FAILED` | 执行失败 | 步骤执行过程中出错 |
| `ADAPTER_NOT_FOUND` | 适配器未找到 | task_id 未绑定 adapter |
| `FREEZE_ERROR` | 冻结处理错误 | 冻结过程中出错 |
| `REPLAN_ERROR` | 重新规划失败 | 重新规划过程中出错 |
| `WEBSOCKET_DISCONNECTED` | WebSocket 断开 | 连接异常断开 |

---

## 八、消息时序图（完整流程）

```
[正常流程]
user_input → task.started → thinking.node_created → 
select_option → thinking.option_selected → thinking.node_selected → 
(loop) → thinking.completed → thinking.converged → 
execution.blueprint_loaded → execution.step_started → execution.step_completed → 
... → execution.completed

[干预流程]
... → execution.step_failed → execution.intervention_needed → 
retry_step → execution.step_started → execution.step_completed → ...

[冻结流程]
... → freeze_request → freeze.confirmed → 
submit_annotation → status_update (resuming) → execution.step_started → ...

[重新规划流程]
... → request_replan → replan.result → 
confirm_replan (accept=true) → execution.blueprint_loaded → ...
```

---

## 九、版本兼容性

| 协议版本 | 前端版本 | 后端版本 | 状态 |
|---------|---------|---------|------|
| V1 | legacy | legacy | 已废弃 |
| V2.0 | `buleclawv1-frontword` | `blueclawv2` | 核心链路已验证 ✅ |
| **V2.1** | `buleclawv1-frontword` | `blueclawv2` | **当前版本**（干预/冻结接口新增） |

### V2.0 → V2.1 变更
- 新增: `freeze_request`, `submit_annotation`, `retry_step`, `request_replan`, `confirm_replan`
- 新增推送: `screenshot`, `status_update`, `freeze.confirmed`, `replan.result`
- 废弃: 无（向后兼容）

---

## 十、文件索引

```
dev_logs/
├── api_specification_unified.md      # 本文档（唯一权威规范）
├── api_changelog.md                   # 变更日志
├── interface_comparison_report.md     # V2 vs specification 对比报告
├── API_INTERFACE_V2.md                # 前端设计愿景（已降级）
├── frontend_architecture.md           # 前端架构
├── backend_architecture.md            # 后端架构
├── testing_guide.md                   # 测试文档
└── deployment_guide.md                # 部署文档
```

---

*文档版本: v2.1.0-unified*  
*更新日期: 2026-04-23*  
*验证状态: E2E 全链路通过（thinking → selection → execution）*
