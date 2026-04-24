# Blueclaw V2 系统架构文档

> 文档版本: 2025-04-04  
> 基于截图验证的端到端方案

---

## 一、系统总览

Blueclaw 是一个基于 AI 的任务规划与执行系统，采用前后端分离架构，通过 WebSocket 实现实时双向通信。

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户 (浏览器)                            │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP / WebSocket
┌─────────────────────────────▼───────────────────────────────────┐
│                    前端 (React 18 + Vite)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ 用户输入界面 │  │ Thinking面板 │  │   Execution画布      │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ WebSocket   │  │ Zustand Store│  │  React Flow 渲染     │   │
│  │  上下文     │  │  状态管理    │  │                     │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ WebSocket (ws://127.0.0.1:8006/ws)
┌─────────────────────────────▼───────────────────────────────────┐
│                  后端 (FastAPI + Uvicorn)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ WebSocket   │  │ Message      │  │   Thinking Engine   │   │
│  │ 连接管理器   │──│   Router     │──│    (思考引擎)        │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  State Sync │  │  Execution   │  │    LLM Provider     │   │
│  │ (状态同步)   │  │   Engine     │  │   (KIMI API)        │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、前端架构

### 2.1 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18 | UI 框架 |
| Vite | latest | 构建工具 |
| TypeScript | latest | 类型安全 |
| Tailwind CSS | latest | 样式系统 |
| Zustand | latest | 全局状态管理 |
| React Flow | latest | 节点图渲染 |
| Playwright | 1.59.1 | E2E 测试 |

### 2.2 功能模块

#### 2.2.1 用户输入模块
- **位置**: `src/components/` (输入区域组件)
- **功能**: 
  - 接收用户自然语言输入
  - 发送 `user_input` 消息启动任务
  - 显示当前任务状态标签（"思考中"/"执行中"）
- **调用接口**: 通过 `WebSocketContext.send('user_input', payload)`

#### 2.2.2 Thinking 面板
- **位置**: `src/components/nodes/ThinkingNode.tsx`
- **功能**:
  - 显示思考节点列表（垂直堆叠）
  - 节点展开/折叠（点击头部切换）
  - 选项选择（A/B/C... 方案按钮）
  - 自定义输入（可选）
  - "重新思考"按钮
  - 已选择状态显示（"已选择: xxx"）
- **调用接口**: 
  - 选项点击 → `send('thinking.select_option', {current_node_id, option_id})`
  - 自定义输入 → `send('thinking.custom_input', {current_node_id, custom_input})`

#### 2.2.3 Execution 画布
- **位置**: `src/components/` (执行流程图区域)
- **功能**:
  - 使用 React Flow 渲染执行流程图
  - 显示执行步骤节点和连接线
  - 节点状态指示（待执行/执行中/已完成/失败）
  - 支持缩放、平移、拖拽
- **数据来源**: `execution.blueprint_loaded` 消息推送的蓝图数据

#### 2.2.4 干预面板
- **功能**: 当执行步骤需要人工干预时弹出
- **触发**: `execution.intervention_needed` 消息

### 2.3 状态管理 (Zustand Store)

**文件**: `src/store/useBlueprintStore.ts`

```typescript
interface BlueprintState {
  // 阶段
  phase: 'idle' | 'thinking' | 'execution' | 'completed';
  
  // Thinking 阶段
  thinkingNodes: ThinkingNode[];
  currentThinkingIndex: number;
  selectedThinkingNodeId: string | null;
  
  // Execution 阶段
  executionSteps: ExecutionStep[];
  selectedExecutionStepId: string | null;
  
  // 干预
  interventionVisible: boolean;
  interventionStepId: string | null;
  
  // Actions
  setPhase: (phase: string) => void;
  setThinkingNodes: (nodes: ThinkingNode[]) => void;
  updateThinkingNode: (id: string, updates: Partial<ThinkingNode>) => void;
  selectThinkingOption: (nodeId: string, optionId: string) => void;
  setCurrentThinkingIndex: (index: number) => void;
  setSelectedThinkingNodeId: (id: string | null) => void;
  setExecutionSteps: (steps: ExecutionStep[]) => void;
  updateExecutionStep: (stepId: string, updates: Partial<ExecutionStep>) => void;
  selectExecutionStep: (stepId: string | null) => void;
  showIntervention: (stepId: string) => void;
  hideIntervention: () => void;
}
```

### 2.4 WebSocket 通信层

**文件**: `src/context/WebSocketContext.tsx`

#### React 18 批处理兼容模式
使用 `messagesRef` + `messageVersion` + `consumeMessages()` 模式解决 React 18 自动批处理导致的 WS 消息丢失问题：

```typescript
// 消息队列存储在 ref 中（绕过 React 批处理）
const messagesRef = useRef<WebSocketMessage[]>([]);
// 版本号触发消费
const [messageVersion, setMessageVersion] = useState(0);

const consumeMessages = () => {
  const msgs = messagesRef.current;
  messagesRef.current = [];
  return msgs;
};

// WS onmessage 回调
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  messagesRef.current.push(msg);
  setMessageVersion(v => v + 1); // 触发 React 重新渲染
};
```

#### WebSocketContext API

```typescript
interface WebSocketContextValue {
  isConnected: boolean;           // 连接状态
  messageVersion: number;         // 消息版本（用于触发消费）
  consumeMessages: () => WebSocketMessage[];  // 消费消息队列
  send: (type: string, payload: any) => void; // 发送消息
  connect: () => void;            // 手动连接
  disconnect: () => void;         // 手动断开
}
```

### 2.5 实时消息处理

**文件**: `src/components/RealtimeProvider.tsx`

RealtimeProvider 消费 `consumeMessages()` 并根据消息类型更新 Zustand store：

| 后端消息 | 前端处理 |
|---------|---------|
| `task.started` | 设置用户输入文本，切换 phase 到 'thinking' |
| `thinking.node_created` | 添加新节点到 thinkingNodes，设置 currentThinkingIndex |
| `thinking.node_selected` | 同上（非根节点） |
| `thinking.option_selected` | 更新节点状态为 'selected'，记录 selectedOption |
| `thinking.completed` | 标记思考完成 |
| `thinking.converged` | 标记思考收敛 |
| `execution.blueprint_loaded` | 加载执行步骤，切换 phase 到 'execution' |
| `execution.step_started` | 更新步骤状态为 'running' |
| `execution.step_completed` | 更新步骤状态为 'completed'，记录结果 |
| `execution.step_failed` | 更新步骤状态为 'failed'，记录错误 |
| `execution.intervention_needed` | 显示干预面板 |
| `execution.returned_to_thinking` | 切换 phase 回 'thinking' |
| `error` | 控制台输出错误 |

### 2.6 前端 → 后端消息映射

| 用户操作 | 前端发送 | 后端处理 |
|---------|---------|---------|
| 提交任务 | `user_input` | `_handle_task_start` |
| 选择选项 | `select_option` (V2) | `_handle_thinking_select_option` |
| 自定义输入 | `custom_input` (V2) | `_handle_thinking_custom_input` |

**注意**: 前端发送的 V2 消息 payload 中 `task_id: ''`，后端 `message_router.py` 会自动从 WebSocket 连接元数据推断 `task_id`。

---

## 三、后端架构

### 3.1 技术栈

| 技术 | 用途 |
|------|------|
| FastAPI | Web 框架 |
| Uvicorn | ASGI 服务器 |
| WebSocket | 实时双向通信 |
| SQLite | 数据持久化 |
| KIMI API | LLM 推理服务 |

### 3.2 功能模块

#### 3.2.1 WebSocket 连接管理
**文件**: `backend/websocket/` 相关模块

- 维护 `connections` 字典: `websocket → {task_id, client_info}`
- 支持多客户端连接同一任务
- 连接断开时自动清理

#### 3.2.2 消息路由 (Message Router)
**文件**: `backend/websocket/message_router.py`

```python
class MessageRouter:
    handlers: Dict[str, Callable] = {
        'user_input': _handle_task_start,
        'select_option': _handle_thinking_select_option,
        'custom_input': _handle_thinking_custom_input,
        # ... 其他处理器
    }
```

**核心功能**:
- `route(websocket, message, server)` — 消息分发入口
- `_get_task_id(websocket, server)` — 从连接元数据自动推断 task_id
- 自动注入 `task_id` 到 payload（解决前端 V2 发送空 task_id 的问题）

#### 3.2.3 Thinking Engine (思考引擎)
**文件**: `blueclaw/core/thinking_engine.py`

```python
class ThinkingEngine:
    MAX_DEPTH = 3              # 最大思考深度
    AUTO_SELECT_THRESHOLD = 0.85  # 自动选择置信度阈值
    
    async def select_option_impl(task_id, node_id, option_id, custom_input=None):
        # 1. 标记当前节点选择
        # 2. 检查是否达到 MAX_DEPTH
        # 3. 生成下一个思考节点
        # 4. 检查是否触发 auto-select
        # 5. 递归处理或返回新节点
```

**思考流程**:
1. 用户输入 → 生成根思考节点（问题 + 选项列表）
2. 用户选择选项 → 生成子节点（更细化的问题）
3. 重复直到 `depth >= MAX_DEPTH` → 思考收敛
4. 收敛后生成执行蓝图

**自动选择逻辑**:
- 当某个选项的 `confidence >= AUTO_SELECT_THRESHOLD` 时自动选择
- 避免不必要的用户干预

#### 3.2.4 State Sync (状态同步)
**文件**: `blueclaw/core/state_sync.py`

负责将后端状态变更通过 WebSocket 广播给所有连接的客户端：

```python
class StateSyncManager:
    async def push_thinking_node_created(task_id, node): ...
    async def push_thinking_node_selected(task_id, node): ...
    async def push_thinking_option_selected(task_id, node_id, option_id): ...
    async def push_thinking_completed(task_id): ...
    async def push_thinking_converged(task_id): ...
    async def push_execution_blueprint_loaded(task_id, blueprint): ...
    async def push_execution_step_started(task_id, step_id): ...
    async def push_execution_step_completed(task_id, step_id, result): ...
    async def push_execution_step_failed(task_id, step_id, error): ...
    async def push_execution_intervention_needed(task_id, step_id): ...
    async def push_execution_returned_to_thinking(task_id): ...
```

#### 3.2.5 执行引擎
- 接收思考收敛后的蓝图
- 按顺序执行步骤
- 每个步骤可调用外部工具/API
- 步骤失败时触发干预或重试

### 3.3 后端入口

| 文件 | 用途 |
|------|------|
| `backend/main.py` | 主入口（开发模式） |
| `backend/unified_server.py` | 统一服务器入口 |

---

## 四、接口层规范

### 4.1 通信协议

- **协议**: WebSocket over TCP
- **地址**: `ws://127.0.0.1:8006/ws`
- **编码**: JSON
- **连接模式**: 持久连接，支持自动重连

### 4.2 消息格式 (V2)

所有消息统一使用以下格式：

```json
{
  "type": "message_type",
  "payload": { ... },
  "message_id": "uuid-v4",
  "timestamp": "2025-04-04T12:00:00.000Z"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 消息类型标识 |
| `payload` | object | 是 | 消息载荷 |
| `message_id` | string | 否 | 唯一消息 ID（用于去重） |
| `timestamp` | string | 否 | ISO 8601 时间戳 |

### 4.3 前端 → 后端接口

#### 4.3.1 启动任务
```json
{
  "type": "user_input",
  "payload": {
    "user_input": "Plan a weekend trip to Hangzhou",
    "task_id": ""
  }
}
```

**说明**: `task_id` 可为空字符串，后端自动推断。

#### 4.3.2 选择思考选项
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

#### 4.3.3 自定义输入
```json
{
  "type": "custom_input",
  "payload": {
    "task_id": "",
    "current_node_id": "thinking_879ebf59",
    "custom_input": "我的自定义方案"
  }
}
```

### 4.4 后端 → 前端接口

#### 4.4.1 任务启动确认
```json
{
  "type": "task.started",
  "payload": {
    "task_id": "task_xxx",
    "user_input": "Plan a weekend trip to Hangzhou"
  }
}
```

#### 4.4.2 思考节点创建
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
        },
        {
          "id": "B",
          "label": "自然风光之旅",
          "description": "主要游览杭州的自然风光...",
          "confidence": 0.78,
          "recommended": false
        }
      ],
      "status": "pending",
      "depth": 0
    }
  }
}
```

#### 4.4.3 思考节点选择（非根节点）
```json
{
  "type": "thinking.node_selected",
  "payload": {
    "node": { ... }
  }
}
```

#### 4.4.4 选项已选择
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

#### 4.4.5 思考完成
```json
{
  "type": "thinking.completed",
  "payload": {
    "task_id": "task_xxx",
    "final_path": ["thinking_879ebf59", "thinking_7e7d11ae"]
  }
}
```

#### 4.4.6 思考收敛
```json
{
  "type": "thinking.converged",
  "payload": {
    "task_id": "task_xxx",
    "convergence_reason": "max_depth_reached"
  }
}
```

#### 4.4.7 执行蓝图加载
```json
{
  "type": "execution.blueprint_loaded",
  "payload": {
    "blueprint": {
      "steps": [
        {
          "id": "step_1",
          "name": "信息检索",
          "description": "检索杭州旅游相关信息",
          "status": "pending",
          "dependencies": []
        },
        {
          "id": "step_2",
          "name": "交通查询",
          "description": "查询往返交通方案",
          "status": "pending",
          "dependencies": ["step_1"]
        },
        {
          "id": "step_3",
          "name": "预算分析",
          "description": "分析旅行预算",
          "status": "pending",
          "dependencies": ["step_2"]
        },
        {
          "id": "step_4",
          "name": "对比价格方案",
          "description": "对比不同方案价格",
          "status": "pending",
          "dependencies": ["step_3"]
        },
        {
          "id": "step_5",
          "name": "住宿查询",
          "description": "查询住宿信息",
          "status": "pending",
          "dependencies": ["step_1"]
        },
        {
          "id": "step_6",
          "name": "生成最终方案",
          "description": "生成最终旅行方案",
          "status": "pending",
          "dependencies": ["step_4", "step_5"]
        }
      ]
    }
  }
}
```

#### 4.4.8 执行步骤开始
```json
{
  "type": "execution.step_started",
  "payload": {
    "step_id": "step_1",
    "timestamp": "2025-04-04T12:01:00.000Z"
  }
}
```

#### 4.4.9 执行步骤完成
```json
{
  "type": "execution.step_completed",
  "payload": {
    "step_id": "step_1",
    "result": { ... },
    "timestamp": "2025-04-04T12:01:05.000Z"
  }
}
```

#### 4.4.10 执行步骤失败
```json
{
  "type": "execution.step_failed",
  "payload": {
    "step_id": "step_2",
    "error": "API timeout",
    "timestamp": "2025-04-04T12:01:10.000Z"
  }
}
```

#### 4.4.11 需要干预
```json
{
  "type": "execution.intervention_needed",
  "payload": {
    "step_id": "step_3",
    "reason": "需要用户确认预算范围",
    "context": { ... }
  }
}
```

#### 4.4.12 返回思考
```json
{
  "type": "execution.returned_to_thinking",
  "payload": {
    "task_id": "task_xxx",
    "reason": "执行失败，需要重新思考"
  }
}
```

#### 4.4.13 错误
```json
{
  "type": "error",
  "payload": {
    "message": "Unknown message type: xxx",
    "code": "UNKNOWN_TYPE"
  }
}
```

### 4.5 接口架构图

```
                    ┌─────────────────┐
                    │     前端        │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
  ┌────────────┐     ┌────────────┐     ┌────────────┐
  │ user_input │     │select_option│    │custom_input│
  └─────┬──────┘     └─────┬──────┘     └─────┬──────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Message    │
                    │   Router    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
  ┌────────────┐   ┌──────────────┐   ┌────────────┐
  │   Task     │   │   Thinking   │   │  Custom    │
  │   Start    │   │   Select     │   │  Input     │
  └─────┬──────┘   └──────┬───────┘   └─────┬──────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                   ┌──────▼──────┐
                   │   State     │
                   │   Sync      │
                   └──────┬──────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
  ┌────────────┐  ┌──────────────┐  ┌────────────┐
  │  thinking  │  │   execution  │  │   error    │
  │   events   │  │    events    │  │   events   │
  └─────┬──────┘  └──────┬───────┘  └─────┬──────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                  ┌──────▼──────┐
                  │   WebSocket │
                  │  Broadcast  │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │     前端     │
                  └─────────────┘
```

### 4.6 消息时序图

```
前端                  后端(WS)              Thinking Engine           LLM
 │                       │                        │                    │
 │── user_input ────────▶│                        │                    │
 │                       │── start_task ────────▶│                    │
 │                       │                        │── generate root ──▶│
 │                       │                        │◀── node data ─────│
 │◀─ task.started ───────│                        │                    │
 │◀─ thinking.node_created│                       │                    │
 │                       │                        │                    │
 │── select_option ─────▶│                        │                    │
 │                       │── select_option_impl ─▶│                    │
 │                       │                        │── generate child ─▶│
 │                       │                        │◀── node data ─────│
 │◀─ thinking.option_selected ─────────────────────────────────────────│
 │◀─ thinking.node_selected ───────────────────────────────────────────│
 │                       │                        │                    │
 │── select_option ─────▶│                        │                    │
 │                       │── select_option_impl ─▶│                    │
 │                       │                        │ (depth >= MAX_DEPTH)
 │                       │                        │── generate blueprint│
 │◀─ thinking.option_selected ─────────────────────────────────────────│
 │◀─ thinking.completed ───────────────────────────────────────────────│
 │◀─ thinking.converged ───────────────────────────────────────────────│
 │◀─ execution.blueprint_loaded ───────────────────────────────────────│
 │                       │                        │                    │
 │                       │◀── execute_step ──────│                    │
 │◀─ execution.step_started ───────────────────────────────────────────│
 │                       │── step result ───────▶│                    │
 │◀─ execution.step_completed ─────────────────────────────────────────│
 │                       │ (repeat for all steps)                     │
```

---

## 五、数据模型

### 5.1 ThinkingNode

```typescript
interface ThinkingNode {
  id: string;              // 节点 ID，如 "thinking_879ebf59"
  question: string;         // 问题文本
  options: ThinkingOption[]; // 选项列表
  status: 'pending' | 'selected' | 'resolved'; // 节点状态
  selectedOption?: string;  // 已选择的选项 ID
  depth: number;            // 思考深度（0-based）
  parentId?: string;        // 父节点 ID
}

interface ThinkingOption {
  id: string;               // 选项 ID，如 "A", "B"
  label: string;            // 选项标签
  description: string;      // 选项描述
  confidence: number;       // 置信度 (0-1)
  recommended: boolean;     // 是否推荐
}
```

### 5.2 ExecutionStep

```typescript
interface ExecutionStep {
  id: string;               // 步骤 ID，如 "step_1"
  name: string;             // 步骤名称
  description: string;      // 步骤描述
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;             // 执行结果
  error?: string;           // 错误信息
  dependencies: string[];   // 依赖步骤 ID 列表
}
```

---

## 六、关键设计决策

### 6.1 React 18 批处理兼容
React 18 的自动批处理会导致 WebSocket `onmessage` 回调中的 `setState` 被批量处理，造成消息丢失。解决方案：
- 使用 `useRef` 存储消息队列（绕过批处理）
- 使用版本号触发重新渲染
- 在 `useEffect` 中通过 `consumeMessages()` 批量消费

### 6.2 Task ID 自动推断
前端 V2 协议中 `task_id` 为空字符串，后端通过以下逻辑推断：
1. 检查 server 是否有 `get_task_id_for_connection()` 方法
2. 检查 `server.connections[websocket]` 中的 `task_id` 字段
3. 自动注入到 payload 中再传递给 handler

### 6.3 Thinking 节点自动展开
当 `selectedThinkingNodeId === nodeId` 时，通过 `useEffect` 自动设置 `isExpanded(true)`，确保用户始终看到当前需要交互的节点。

### 6.4 消息去重
`RealtimeProvider` 使用 `Set<string>` 存储已处理消息的 `message_id`，防止重复处理同一消息。

---

## 七、文件目录结构

```
blueclawv2/
├── buleclawv1-frontword/          # 前端项目
│   ├── src/
│   │   ├── components/
│   │   │   ├── nodes/
│   │   │   │   └── ThinkingNode.tsx    # 思考节点组件
│   │   │   ├── RealtimeProvider.tsx    # WS 消息处理器
│   │   │   └── ...
│   │   ├── context/
│   │   │   └── WebSocketContext.tsx    # WS 连接管理
│   │   ├── store/
│   │   │   └── useBlueprintStore.ts    # Zustand 状态管理
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── websocket/
│   │   └── message_router.py          # 消息路由
│   ├── main.py                         # 开发入口
│   └── unified_server.py               # 统一服务器入口
│
├── blueclaw/
│   ├── core/
│   │   ├── thinking_engine.py          # 思考引擎
│   │   └── state_sync.py               # 状态同步
│   └── ...
│
├── .env                                 # 环境变量 (KIMI_API_KEY)
└── ARCHITECTURE_DOCUMENT.md             # 本文档
```

---

## 八、测试验证

已通过 Playwright E2E 测试验证完整流程：

```
用户输入 → Thinking Node 1 → 选择选项 A → Thinking Node 2 → 选择选项 A
  → Thinking 收敛 → Execution 蓝图加载 → 步骤执行 (6 steps)
```

测试脚本: `test_click_v2.py`
