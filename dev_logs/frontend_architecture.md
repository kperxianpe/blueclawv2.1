# 前端架构文档

> 文档版本: 2025-04-04  
> 对应项目: `blueclawv2/buleclawv1-frontword/`

---

## 一、技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18 | UI 框架 |
| Vite | latest | 构建工具 + 开发服务器 |
| TypeScript | latest | 类型安全 |
| Tailwind CSS | latest | 原子化样式系统 |
| Zustand | latest | 全局状态管理 |
| React Flow | latest | 节点图/流程图渲染 |
| Playwright | 1.59.1 | E2E 自动化测试 |

---

## 二、功能模块

### 2.1 用户输入模块

**位置**: `src/components/` 顶部输入区域

**功能清单**:
- 接收用户自然语言输入（如 "Plan a weekend trip to Hangzhou"）
- 发送 `user_input` 消息启动任务
- 显示当前任务状态标签（"思考中" / "执行中" / "已完成"）
- 重置/清空功能

**如何调用接口**:
```typescript
import { useWebSocketContext } from '../context/WebSocketContext';

const { send } = useWebSocketContext();

// 用户点击提交按钮时
const handleSubmit = (userInput: string) => {
  send('user_input', {
    user_input: userInput,
    task_id: ''  // 后端自动推断
  });
};
```

---

### 2.2 Thinking 面板

**位置**: `src/components/nodes/ThinkingNode.tsx`

**功能清单**:
- 显示思考节点列表（垂直堆叠，自上而下）
- 节点展开/折叠（点击节点头部切换）
- 选项选择（A/B/C... 方案按钮，带描述和置信度）
- 自定义输入框（当没有合适选项时使用）
- "重新思考"按钮（放弃当前分支，重新生成）
- 已选择状态显示（折叠后显示 "已选择: xxx"）
- 节点 ID 显示（如 "思考节点 #879ebf59"）
- 自动展开当前选中节点

**界面元素**:
```
┌─────────────────────────────┐
│ 🧠 您计划周末去杭州旅行...   │ ← 节点头部（可点击展开/折叠）
│    文化之旅                   │ ← 已选择摘要
│    ▲                          │ ← 展开指示器
├─────────────────────────────┤
│ 思考节点 #879ebf59            │
│ [重新思考]                    │
│                             │
│ 选择方案:                     │
│ ┌─────────────────────────┐ │
│ │ A. 文化探索之旅          │ │ ← 选项按钮
│ │    探索杭州的历史文化...  │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ B. 自然风光之旅          │ │
│ │    主要游览杭州的自然...  │ │
│ └─────────────────────────┘ │
│ [其他自定义输入...]           │
└─────────────────────────────┘
```

**如何调用接口** — 选项选择:
```typescript
const { isConnected, send } = useWebSocketContext();

const handleOptionClick = (optionId: string) => {
  if (phase !== 'thinking') return;
  if (isConnected) {
    // WebSocket 模式：发送到后端
    send('thinking.select_option', {
      task_id: '',
      current_node_id: nodeId,
      option_id: optionId
    });
  } else {
    // Mock 模式：本地更新 store（离线调试）
    selectThinkingOption(nodeId, optionId);
  }
};
```

**如何调用接口** — 自定义输入:
```typescript
const handleCustomInput = (customText: string) => {
  if (isConnected) {
    send('thinking.custom_input', {
      task_id: '',
      current_node_id: nodeId,
      custom_input: customText
    });
  } else {
    setCustomInput(nodeId, customText);
  }
};
```

---

### 2.3 Execution 画布

**位置**: 主界面右侧/中央区域（React Flow 容器）

**功能清单**:
- 使用 React Flow 渲染执行流程图
- 显示执行步骤节点（矩形卡片，含图标、名称、状态）
- 节点间连接线（带箭头，表示依赖关系）
- 节点状态指示：
  - 🟡 橙色 = 待执行
  - 🟢 绿色 = 执行中 / 已完成
  - 🔴 红色 = 失败
- 支持画布操作：缩放（滚轮）、平移（拖拽空白处）、拖拽节点
- 步骤详情面板（点击节点查看）

**数据来源**:
```typescript
// execution.blueprint_loaded 消息到达后
const steps = msg.payload.blueprint.steps;
setExecutionSteps(steps);
setPhase('execution');
```

---

### 2.4 干预面板

**功能清单**:
- 当执行步骤需要人工确认/输入时弹出模态框
- 显示干预原因和上下文
- 提供输入框让用户补充信息
- 确认后发送干预响应，继续执行

**触发条件**:
```typescript
// RealtimeProvider 中处理
 case 'execution.intervention_needed':
   showIntervention(msg.payload.step_id);
   break;
```

---

## 三、状态管理 (Zustand Store)

**文件**: `src/store/useBlueprintStore.ts`

### 3.1 State 结构

```typescript
interface BlueprintState {
  // === 阶段控制 ===
  phase: 'idle' | 'thinking' | 'execution' | 'completed';
  
  // === Thinking 阶段 ===
  thinkingNodes: ThinkingNode[];        // 所有思考节点
  currentThinkingIndex: number;          // 当前节点索引
  selectedThinkingNodeId: string | null; // 当前选中节点 ID
  
  // === Execution 阶段 ===
  executionSteps: ExecutionStep[];       // 执行步骤列表
  selectedExecutionStepId: string | null;// 当前选中步骤 ID
  
  // === 干预 ===
  interventionVisible: boolean;
  interventionStepId: string | null;
  
  // === 用户输入 ===
  userInput: string;
}

interface ThinkingNode {
  id: string;               // e.g. "thinking_879ebf59"
  question: string;         // 节点问题文本
  options: ThinkingOption[];
  status: 'pending' | 'selected' | 'resolved';
  selectedOption?: string;  // 选中的 option_id
  depth: number;            // 思考深度 0,1,2...
}

interface ThinkingOption {
  id: string;               // "A", "B"...
  label: string;            // "文化探索之旅"
  description: string;      // 详细描述
  confidence: number;       // 0.0 ~ 1.0
  recommended: boolean;     // 是否高置信度推荐
}

interface ExecutionStep {
  id: string;               // "step_1"
  name: string;             // "信息检索"
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
  dependencies: string[];
}
```

### 3.2 Actions 列表

| Action | 用途 | 调用场景 |
|--------|------|---------|
| `setPhase(phase)` | 切换阶段 | WS 消息驱动 |
| `setThinkingNodes(nodes)` | 设置/覆盖节点列表 | 初始化 |
| `updateThinkingNode(id, updates)` | 更新单个节点 | option_selected |
| `selectThinkingOption(nodeId, optionId)` | Mock 模式下选择 | 离线调试 |
| `setCurrentThinkingIndex(index)` | 设置当前索引 | node_created |
| `setSelectedThinkingNodeId(id)` | 设置选中节点 | node_created/点击 |
| `setExecutionSteps(steps)` | 设置执行步骤 | blueprint_loaded |
| `updateExecutionStep(id, updates)` | 更新步骤状态 | step_started/completed |
| `selectExecutionStep(id)` | 选中步骤 | blueprint_loaded |
| `showIntervention(stepId)` | 显示干预 | intervention_needed |
| `hideIntervention()` | 隐藏干预 | 用户响应后 |
| `setUserInput(text)` | 设置用户输入 | task.started |
| `setCustomInput(nodeId, text)` | Mock 自定义输入 | 离线调试 |

### 3.3 Store 全局暴露（E2E 调试）

```typescript
// 文件末尾
if (typeof window !== 'undefined') {
  (window as any).__BLUECLAW_STORE__ = useBlueprintStore;
}
```

E2E 测试可通过 `page.evaluate` 直接读取 store 状态：
```javascript
window.__BLUECLAW_STORE__.getState().phase
window.__BLUECLAW_STORE__.getState().thinkingNodes.length
```

---

## 四、WebSocket 通信层

### 4.1 核心文件

- **`src/context/WebSocketContext.tsx`** — WS 连接管理上下文
- **`src/components/RealtimeProvider.tsx`** — 消息消费与状态映射

### 4.2 React 18 批处理兼容方案

**问题**: React 18 的自动批处理导致 WebSocket `onmessage` 中的 `setState` 被批量合并，高频消息会丢失。

**解决方案** — `messagesRef` + `messageVersion` 模式:

```typescript
// WebSocketContext.tsx
const messagesRef = useRef<WebSocketMessage[]>([]);
const [messageVersion, setMessageVersion] = useState(0);

// WS 收到消息时，存入 ref（不触发渲染）
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  messagesRef.current.push(msg);
  setMessageVersion(v => v + 1); // 仅更新版本号触发一次渲染
};

// 提供消费方法
const consumeMessages = () => {
  const msgs = messagesRef.current;
  messagesRef.current = []; // 清空队列
  return msgs;
};
```

```typescript
// RealtimeProvider.tsx
const { messageVersion, consumeMessages } = useWebSocketContext();

useEffect(() => {
  const messages = consumeMessages();
  if (messages.length === 0) return;
  
  for (const msg of messages) {
    // 去重检查
    const msgId = msg.message_id || `${msg.type}_${msg.timestamp}`;
    if (processedMessages.current.has(msgId)) continue;
    processedMessages.current.add(msgId);
    
    // 根据 type 分发到 store actions
    switch (msg.type) {
      case 'thinking.node_created': ...
      case 'thinking.option_selected': ...
      // ... 其他消息类型
    }
  }
}, [messageVersion]); // 依赖版本号，不依赖消息内容
```

### 4.3 WebSocketContext API

```typescript
interface WebSocketContextValue {
  isConnected: boolean;                      // 是否已连接
  messageVersion: number;                    // 消息版本计数器
  consumeMessages: () => WebSocketMessage[]; // 消费并返回所有新消息
  send: (type: string, payload: any) => void; // 发送消息到后端
  connect: () => void;                       // 手动连接
  disconnect: () => void;                    // 手动断开
}
```

### 4.4 重连逻辑

```typescript
// WebSocketContext 内置
- 连接断开时自动触发重连
- 指数退避延迟（1s → 2s → 4s → ... 最大 30s）
- 最大重试次数：无限制（持续尝试）
- 连接成功后发送 pending 消息队列
```

---

## 五、后端消息 → 前端处理映射

| 后端消息类型 | RealtimeProvider 处理 | 影响的 Store 状态 |
|------------|---------------------|------------------|
| `task.started` | 记录 userInput，切换 phase | `userInput`, `phase='thinking'` |
| `thinking.node_created` | 添加节点到列表 | `thinkingNodes[]`, `currentThinkingIndex`, `selectedThinkingNodeId` |
| `thinking.node_selected` | 同上（非根节点） | 同上 |
| `thinking.option_selected` | 更新节点状态 | `updateThinkingNode(status='selected')` |
| `thinking.completed` | 标记完成 | 无直接状态变更（日志记录） |
| `thinking.converged` | 标记收敛 | 无直接状态变更（日志记录） |
| `execution.blueprint_loaded` | 加载蓝图 | `executionSteps[]`, `phase='execution'`, `selectedExecutionStepId` |
| `execution.step_started` | 更新步骤状态 | `updateExecutionStep(status='running')` |
| `execution.step_completed` | 更新步骤+结果 | `updateExecutionStep(status='completed', result)` |
| `execution.step_failed` | 更新步骤+错误 | `updateExecutionStep(status='failed', error)` |
| `execution.intervention_needed` | 显示干预 | `interventionVisible=true`, `interventionStepId` |
| `execution.returned_to_thinking` | 返回思考 | `phase='thinking'` |
| `error` | 控制台报错 | 无 |

---

## 六、关键设计决策

### 6.1 React 18 批处理兼容
- **原因**: React 18 自动批处理导致高频 WS 消息丢失
- **方案**: `useRef` 存储消息队列 + 版本号触发消费
- **效果**: 所有 WS 消息被可靠消费，无丢失

### 6.2 ThinkingNode 自动展开
```typescript
// ThinkingNode.tsx
const isSelected = selectedNodeId === nodeId;

useEffect(() => {
  if (isSelected) {
    setIsExpanded(true); // 自动展开当前节点
  }
}, [isSelected]);
```
- **原因**: 用户需要看到当前可交互的节点
- **效果**: 节点被选中时自动展开，显示选项按钮

### 6.3 Mock / WebSocket 双模式
```typescript
const { isConnected, send } = useWebSocketContext();

if (isConnected) {
  send('thinking.select_option', {...}); // 真实后端
} else {
  selectThinkingOption(nodeId, optionId); // Mock 本地
}
```
- **原因**: 支持离线开发和前端独立调试
- **效果**: 无后端时前端仍可演示完整流程

### 6.4 消息去重
```typescript
const processedMessages = useRef<Set<string>>(new Set());
// 使用 message_id 或生成唯一标识
// Set 大小超过 1000 时自动清空（防止内存泄漏）
```

---

## 七、文件目录

```
buleclawv1-frontword/
├── src/
│   ├── components/
│   │   ├── nodes/
│   │   │   └── ThinkingNode.tsx      # 思考节点组件（展开/折叠/选项/自定义输入）
│   │   ├── RealtimeProvider.tsx       # WS 消息消费 + store 映射
│   │   └── ...                        # 其他 UI 组件
│   │
│   ├── context/
│   │   └── WebSocketContext.tsx       # WS 连接、重连、消息队列
│   │
│   ├── store/
│   │   └── useBlueprintStore.ts       # Zustand 全局状态
│   │
│   ├── types/
│   │   └── ...                        # TypeScript 类型定义
│   │
│   ├── App.tsx                        # 根组件
│   └── main.tsx                       # 入口
│
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 八、调试指南

### 8.1 浏览器控制台调试
```javascript
// 查看 store 状态
window.__BLUECLAW_STORE__.getState()

// 监听状态变化
window.__BLUECLAW_STORE__.subscribe(console.log)

// 手动触发 action
window.__BLUECLAW_STORE__.getState().setPhase('execution')
```

### 8.2 WebSocket 消息日志
前端控制台会输出所有 WS 收发消息：
```
[WS] Send: thinking.select_option {...}
[WS] Received: thinking.node_selected
[RealtimeProvider] Processing: thinking.node_selected
```
