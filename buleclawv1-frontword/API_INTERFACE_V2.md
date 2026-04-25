# Blueclaw V1 前后端接口层对接文档

> **版本**: v2.0（基于 2026-04-22 前端代码更新）
> **适用对象**: 后端开发团队
> **前置阅读**: Blueclaw_AI_Canvas_API_Specification.md

---

## 一、文档说明

本文档定义**前端已完成的功能**所需的**后端接口**。前端代码已完成，后端需按此文档实现对应 WebSocket 事件处理器和数据结构。

**关键变更（2026-04-22）**:
1. **干预面板改造**: 从「大弹窗」改为「节点旁小图标按钮组」（▶️🧠❄️）
2. **冻结交互改造**: 从「模糊遮罩+折叠菜单」改为「半透明遮罩+底部状态栏平铺按钮」
3. **新增 FreezeOverlay 组件**: 截图框 + 小思考蓝图节点

---

## 二、核心数据模型

### 2.1 AppPhase（应用阶段）
```typescript
type AppPhase = 'input' | 'thinking' | 'execution' | 'completed';
```

| 阶段 | 说明 |
|------|------|
| `input` | 初始状态，等待用户输入 |
| `thinking` | 生成思考蓝图，用户选择选项 |
| `execution` | 执行生成的执行蓝图 |
| `completed` | 所有步骤执行完成 |

### 2.2 ThinkingNodeType（思考节点）
```typescript
interface ThinkingNodeType {
  id: string;                    // 格式: "thinking_XXX"
  question: string;              // 向用户提出的问题
  options: ThinkingOption[];     // 选项列表（A/B/C/D）
  allowCustom: boolean;          // 是否允许自定义输入
  status: 'pending' | 'selected';
  selectedOption?: string;       // 已选选项ID
  customInput?: string;          // 自定义输入文本
}

interface ThinkingOption {
  id: string;                    // 'A' | 'B' | 'C' | 'D'
  label: string;                 // 选项标签
  description: string;           // 选项描述
  confidence: number;            // 置信度 0-1
  isDefault?: boolean;           // AI推荐标记
}
```

### 2.3 ExecutionStep（执行步骤）
```typescript
interface ExecutionStep {
  id: string;                    // 格式: "step_XXX" 或 "branch_XX"
  name: string;                  // 步骤名称
  description: string;           // 步骤描述
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];        // 前置步骤ID列表
  result?: string;               // 执行结果
  error?: string;                // 错误信息
  position: { x: number; y: number };  // 画布位置（后端可不传，前端自动计算）
  
  // 视觉属性
  isMainPath: boolean;           // true=主路径, false=分支
  isConvergence?: boolean;       // true=汇合节点
  convergenceType?: 'parallel' | 'sequential';
  needsIntervention?: boolean;   // 是否需要用户干预
  isArchived?: boolean;          // 干预后是否归档
}
```

### 2.4 CanvasConfig（画布配置）
```typescript
interface CanvasConfig {
  leftRightRatio: number;        // 默认: 2.236
  execTopBottomRatio: number;    // 默认: 2
  thinkingNodeSpacing: number;   // 默认: 180 (px)
  executionNodeSpacing: number;  // 默认: 140 (px)
  canvasBackground: 'gradient' | 'solid' | 'grid' | 'dots';
  backgroundColor: string;       // 默认: '#0f172a'
}
```

---

## 三、WebSocket 通信协议

### 3.1 连接信息

```
协议: WebSocket (wss:// 或 ws://)
路径: /ws/blueprint
心跳: 30秒一次 ping/pong
```

### 3.2 后端 → 前端（Server → Client）

#### 3.2.1 阶段切换事件

```typescript
// 进入思考阶段
{
  type: 'phase_change',
  payload: {
    phase: 'thinking',
    message: '正在分析你的需求...'
  }
}

// 进入执行阶段
{
  type: 'phase_change',
  payload: {
    phase: 'execution',
    message: '思考完成，开始执行蓝图'
  }
}

// 执行完成
{
  type: 'phase_change',
  payload: {
    phase: 'completed',
    message: '所有任务已完成'
  }
}
```

#### 3.2.2 思考节点事件

```typescript
// 新增思考节点（AI生成问题+选项）
{
  type: 'thinking_node_added',
  payload: {
    node: ThinkingNodeType
  }
}

// 用户选择选项后，AI确认并准备下一个节点
{
  type: 'thinking_option_confirmed',
  payload: {
    nodeId: string,
    selectedOption: string,
    nextNode?: ThinkingNodeType  // 若有后续问题
  }
}

// 思考阶段完成，生成执行蓝图
{
  type: 'thinking_completed',
  payload: {
    summary: string,             // 思考总结
    executionBlueprint: ExecutionStep[]  // 生成的执行步骤
  }
}
```

#### 3.2.3 执行步骤事件

```typescript
// 步骤状态变更
{
  type: 'step_status_changed',
  payload: {
    stepId: string,
    status: 'pending' | 'running' | 'completed' | 'failed',
    progress?: number,           // 0-100，用于进度条
    log?: string                 // 实时日志，如"正在查询天气API..."
  }
}

// 步骤完成，返回结果
{
  type: 'step_completed',
  payload: {
    stepId: string,
    result: string,              // 步骤执行结果
    nextSteps?: string[]         // 接下来要执行的步骤ID
  }
}

// 步骤失败
{
  type: 'step_failed',
  payload: {
    stepId: string,
    error: string,               // 错误描述
    recoverable: boolean         // 是否可恢复（是否显示重试按钮）
  }
}

// 步骤需要干预（触发干预面板）
{
  type: 'intervention_required',
  payload: {
    stepId: string,
    reason: string,              // 需要干预的原因
    context: string              // 当前上下文描述
  }
}
```

#### 3.2.4 冻结相关事件（新增）

```typescript
// 执行冻结
{
  type: 'freeze',
  payload: {
    stepId: string,
    stepName: string,            // 显示在底部状态栏
    screenshot?: string          // Base64 截图数据（可选）
  }
}

// 解冻
{
  type: 'unfreeze',
  payload: {
    stepId: string
  }
}

// 小思考蓝图节点生成（冻结模式下）
{
  type: 'mini_thinking_node_added',
  payload: {
    boxId: string,               // 关联的截图框ID
    node: MiniThinkingNode       // 小思考节点数据
  }
}
```

### 3.3 前端 → 后端（Client → Server）

#### 3.3.1 用户输入

```typescript
// 提交用户输入
{
  type: 'user_input',
  payload: {
    input: string                // 用户输入的文本
  }
}
```

#### 3.3.2 思考阶段交互

```typescript
// 选择选项
{
  type: 'select_option',
  payload: {
    nodeId: string,
    optionId: string             // 'A' | 'B' | 'C' | 'D'
  }
}

// 提交自定义输入
{
  type: 'custom_input',
  payload: {
    nodeId: string,
    input: string
  }
}
```

#### 3.3.3 执行阶段交互

```typescript
// 触发干预（点击齿轮按钮）
{
  type: 'intervene',
  payload: {
    stepId: string
  }
}

// 干预动作（点击小图标按钮）
{
  type: 'interference_action',
  payload: {
    stepId: string,
    action: 'reexecute' | 'rethink' | 'freeze'
    // reexecute: 从当前节点重新执行
    // rethink: 从当前节点前开始重新思考
    // freeze: 冻结执行
  }
}

// 旧版干预面板动作（兼容，可废弃）
{
  type: 'intervention_action',
  payload: {
    stepId: string,
    action: 'continue' | 'newBranch' | 'stop'
  }
}
```

#### 3.3.4 冻结模式交互（新增）

```typescript
// 更改蓝图形容
{
  type: 'change_description',
  payload: {
    description: string
  }
}

// 添加解释截图框
{
  type: 'add_screenshot_box',
  payload: {
    type: 'explain',
    x: number,
    y: number,
    width: number,
    height: number
  }
}

// 添加更改截图框
{
  type: 'add_screenshot_box',
  payload: {
    type: 'modify',
    x: number,
    y: number,
    width: number,
    height: number
  }
}

// 选择小思考蓝图选项
{
  type: 'select_mini_option',
  payload: {
    nodeId: string,
    optionId: string
  }
}

// 解除冻结
{
  type: 'unfreeze',
  payload: {}
}
```

---

## 四、Store 接口（前端状态管理）

### 4.1 State 属性

```typescript
interface BlueprintState {
  // 核心状态
  phase: AppPhase;
  userInput: string;
  
  // 思考蓝图
  thinkingNodes: ThinkingNodeType[];
  currentThinkingIndex: number;
  selectedThinkingNodeId: string | null;
  
  // 执行蓝图
  executionSteps: ExecutionStep[];
  selectedExecutionStepId: string | null;
  
  // 干预状态
  showInterventionPanel: boolean;    // 旧版弹窗（可废弃）
  interventionStepId: string | null;
  
  // 冻结状态（新增）
  isFrozen: boolean;
  frozenStepName: string;
  
  // 配置
  canvasConfig: CanvasConfig;
}
```

### 4.2 Actions（前端已实现，后端需对应）

| Action | 说明 | 触发来源 |
|--------|------|---------|
| `setUserInput(input)` | 设置用户输入 | 前端输入框提交 |
| `startThinking()` | 开始思考阶段 | 前端提交后自动调用 |
| `selectThinkingOption(nodeId, optionId)` | 选择思考选项 | 用户点击选项卡片 |
| `setCustomInput(nodeId, input)` | 设置自定义输入 | 用户输入自定义内容 |
| `selectThinkingNode(nodeId)` | 选中思考节点（UI高亮） | 用户点击节点 |
| `completeThinking()` | 完成思考，生成执行蓝图 | AI确认所有选项已选 |
| `startExecution()` | 开始执行 | 思考完成后自动调用 |
| `executeNextStep()` | 执行下一步 | 依赖步骤完成后自动调用 |
| `selectExecutionStep(stepId)` | 选中执行步骤（UI高亮） | 用户点击节点 |
| `interveneExecution(stepId)` | 触发干预 | 用户点击齿轮按钮 |
| `handleIntervention(action)` | 处理干预动作 | 旧版弹窗选择后 |
| `hideIntervention()` | 隐藏干预面板 | 关闭弹窗 |
| `freeze(stepName)` | 冻结执行 | 用户点击冻结按钮 |
| `unfreeze()` | 解除冻结 | 用户点击解除冻结 |

---

## 五、干预功能详细说明（2026-04-22 更新）

### 5.1 干预触发流程

```
用户点击执行节点右上角 ⚙️ 齿轮按钮
           ↓
前端发送: { type: 'intervene', payload: { stepId } }
           ↓
后端接收，标记该步骤 needsIntervention = true
           ↓
后端发送: { type: 'step_status_changed', payload: { stepId, status: 'running', needsIntervention: true } }
           ↓
前端显示: 节点旁弹出小图标按钮组（▶️🧠❄️）
```

### 5.2 小图标按钮组行为

| 图标 | 动作 | 对应事件 | 说明 |
|------|------|---------|------|
| ▶️ (Play) | `reexecute` | `interference_action` | 从当前节点重新执行 |
| 🧠 (Brain) | `rethink` | `interference_action` | 从当前节点前开始重新思考 |
| ❄️ (Snowflake) | `freeze` | `interference_action` | 冻结执行，进入冻结模式 |

**关键交互**: 点击直接执行，无需确认。hover 显示 tooltip 说明。

### 5.3 重新执行（reexecute）后端逻辑

```typescript
function handleReexecute(stepId: string) {
  // 1. 找到当前步骤索引
  const currentIndex = executionSteps.findIndex(s => s.id === stepId);
  
  // 2. 重置当前及后续步骤状态
  executionSteps.forEach((step, idx) => {
    if (idx >= currentIndex) {
      step.status = 'pending';
      step.result = undefined;
      step.error = undefined;
      step.needsIntervention = false;
    }
  });
  
  // 3. 发送状态变更
  broadcast('step_status_changed', { stepId, status: 'pending' });
  
  // 4. 重新开始执行
  executeNextStep();
}
```

### 5.4 重新思考（rethink）后端逻辑

```typescript
function handleRethink(stepId: string) {
  // 1. 找到当前步骤索引
  const currentIndex = executionSteps.findIndex(s => s.id === stepId);
  
  // 2. 归档当前及后续步骤
  executionSteps.forEach((step, idx) => {
    if (idx >= currentIndex) {
      step.isArchived = true;
    }
  });
  
  // 3. 生成干预思考节点
  const completedSteps = executionSteps
    .slice(0, currentIndex)
    .filter(s => s.status === 'completed');
  
  const context = completedSteps
    .map(s => `${s.name}: ${s.result || 'completed'}`)
    .join('; ');
  
  const interventionNode: ThinkingNodeType = {
    id: 'intervention_001',
    question: `在 "${currentStep.name}" 处重新规划。已完成: ${context}。如何调整？`,
    options: [
      { id: 'A', label: '调整当前步骤', description: '修改执行策略', confidence: 0.85 },
      { id: 'B', label: '添加分支步骤', description: '并行执行额外任务', confidence: 0.78 },
      { id: 'C', label: '跳过当前步骤', description: '继续后续执行', confidence: 0.72 },
      { id: 'D', label: '完全重新规划', description: '基于已完成结果重新设计', confidence: 0.80 },
    ],
    allowCustom: true,
    status: 'pending'
  };
  
  // 4. 切换到思考阶段
  broadcast('phase_change', { phase: 'thinking' });
  broadcast('thinking_node_added', { node: interventionNode });
}
```

---

## 六、冻结功能详细说明（2026-04-22 新增）

### 6.1 冻结触发流程

```
用户点击小图标按钮组的 ❄️ 按钮
           ↓
前端发送: { type: 'interference_action', payload: { stepId, action: 'freeze' } }
           ↓
后端接收，发送冻结事件
           ↓
后端发送: { type: 'freeze', payload: { stepId, stepName } }
           ↓
前端显示: FreezeOverlay 组件
```

### 6.2 冻结模式 UI

```
┌─────────────────────────────────────────────────────────┐
│  画布内容（轻微半透明 bg-slate-900/10）                    │
│                                                         │
│  ┌──────────┐  ┌──────────────┐                        │
│  │ 截图框    │  │ 小思考蓝图节点 │  ← 可拖拽           │
│  │ (可选)   │  │ (可选)        │                        │
│  └──────────┘  └──────────────┘                        │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ ❄️已冻结 | 📋更改蓝图形容 💖解释截图 🟡更改截图 🔓解除冻结 │
└─────────────────────────────────────────────────────────┘
   cyan      indigo          pink        amber      emerald
```

### 6.3 底部按钮行为

| 按钮 | 图标 | 颜色 | 对应事件 | 说明 |
|------|------|------|---------|------|
| 已冻结 | ❄️ | cyan | - | 状态指示，不可点击 |
| 更改蓝图形容 | 📋 | indigo | `change_description` | 弹出输入框修改描述 |
| 解释截图 | 💖 | pink | `add_screenshot_box` (type: 'explain') | 添加解释截图框 |
| 更改截图 | 🟡 | amber | `add_screenshot_box` (type: 'modify') | 添加更改截图框 |
| 解除冻结 | 🔓 | emerald | `unfreeze` | 解除冻结，恢复执行 |

### 6.4 截图框 + 小思考蓝图节点

```typescript
// 前端收到 add_screenshot_box 后：
interface ScreenshotBox {
  id: string;
  type: 'explain' | 'modify';
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

// 每个截图框关联一个小思考蓝图节点
interface MiniThinkingNode {
  id: string;
  boxId: string;               // 关联的截图框ID
  question: string;            // "如何解释这张截图？" 或 "如何更改这张截图？"
  x: number;
  y: number;
  status: 'pending' | 'selected';
  selectedOption?: string;
  options: { id: string; label: string; description: string }[];
}
```

**交互流程**:
1. 用户点击「解释截图」按钮
2. 前端生成截图框（用户可调整位置大小）
3. 发送 `add_screenshot_box` 事件给后端
4. 后端生成对应的小思考节点选项
5. 后端发送 `mini_thinking_node_added` 事件
6. 前端显示小思考节点（可拖拽）
7. 用户选择选项后发送 `select_mini_option`
8. 后端处理选择，可生成新的执行步骤或修改现有步骤

---

## 七、后端实现检查清单

### 7.1 必须实现的事件处理器

| 事件类型 | 方向 | 优先级 | 说明 |
|---------|------|--------|------|
| `user_input` | C→S | P0 | 处理用户输入，触发 thinking |
| `select_option` | C→S | P0 | 处理选项选择 |
| `custom_input` | C→S | P0 | 处理自定义输入 |
| `phase_change` | S→C | P0 | 阶段切换通知 |
| `thinking_node_added` | S→C | P0 | 发送思考节点 |
| `thinking_completed` | S→C | P0 | 思考完成，发送执行蓝图 |
| `step_status_changed` | S→C | P0 | 步骤状态变更 |
| `step_completed` | S→C | P0 | 步骤完成通知 |
| `step_failed` | S→C | P0 | 步骤失败通知 |
| `intervene` | C→S | P1 | 触发干预 |
| `interference_action` | C→S | P1 | 干预动作（reexecute/rethink/freeze） |
| `freeze` | S→C | P1 | 冻结通知 |
| `unfreeze` | C→S/C→C | P1 | 解冻 |
| `add_screenshot_box` | C→S | P2 | 添加截图框 |
| `mini_thinking_node_added` | S→C | P2 | 小思考节点 |
| `select_mini_option` | C→S | P2 | 选择小思考选项 |

### 7.2 数据流顺序验证

```
[正常流程]
user_input → phase_change(thinking) → thinking_node_added(xN) → 
thinking_completed → phase_change(execution) → 
step_status_changed(running) → step_completed → 
step_status_changed(running) → step_completed → ... → 
phase_change(completed)

[干预流程]
... → step_status_changed(running) → intervene → 
interference_action(reexecute) → step_status_changed(pending) → 
step_status_changed(running) → ...

[冻结流程]
... → interference_action(freeze) → freeze → 
add_screenshot_box → mini_thinking_node_added → 
select_mini_option → unfreeze → step_status_changed(running) → ...
```

---

## 八、前端组件与事件映射

| 前端组件 | 触发事件 | 接收事件 | 说明 |
|---------|---------|---------|------|
| `InputScreen` | `user_input` | - | 用户输入提交 |
| `ThinkingNode` | `select_option`, `custom_input` | `thinking_node_added` | 思考节点交互 |
| `ExecutionNode` | `intervene`, `interference_action` | `step_status_changed` | 执行节点+干预按钮 |
| `InterferencePanel` | `interference_action` | - | 小图标按钮组（新） |
| `FreezeOverlay` | `add_screenshot_box`, `select_mini_option`, `unfreeze` | `freeze`, `mini_thinking_node_added` | 冻结覆盖层（新） |
| `BlueprintCanvas` | - | `phase_change` | 阶段切换响应 |

---

## 九、错误处理

### 9.1 前端错误显示

```typescript
// 后端发送错误
{
  type: 'error',
  payload: {
    code: string,          // 错误码
    message: string,       // 错误信息
    stepId?: string        // 关联步骤ID（可选）
  }
}
```

### 9.2 常见错误码

| 错误码 | 说明 | 前端响应 |
|--------|------|---------|
| `THINKING_TIMEOUT` | 思考阶段超时 | 显示重试按钮 |
| `EXECUTION_FAILED` | 执行失败 | 标记步骤为 failed |
| `INTERVENGE_ERROR` | 干预处理错误 | 关闭干预面板，显示错误提示 |
| `FREEZE_ERROR` | 冻结处理错误 | 解除冻结，显示错误提示 |
| `WEBSOCKET_DISCONNECTED` | WebSocket断开 | 显示重连按钮 |

---

## 十、附录

### 10.1 前端文件结构（2026-04-22）

```
src/
├── components/
│   ├── BlueprintCanvas.tsx          # 主画布容器（双画布+视觉区域）
│   ├── InputScreen.tsx              # 初始输入屏幕
│   ├── CompletionScreen.tsx         # 完成屏幕
│   ├── Header.tsx                   # 顶部标题栏
│   ├── nodes/
│   │   ├── ThinkingNode.tsx         # 思考节点（选项卡片+展开）
│   │   ├── ExecutionNode.tsx        # 执行节点（齿轮按钮+干涉入口）
│   │   └── SummaryNode.tsx          # 总结节点
│   ├── panels/
│   │   ├── InterventionPanel.tsx    # 旧版干预弹窗（可废弃）
│   │   ├── InterferencePanel.tsx    # **新版干预小图标按钮组** ⭐
│   │   ├── FreezeOverlay.tsx        # **冻结覆盖层** ⭐
│   │   ├── DetailPanel.tsx          # 详情面板
│   │   └── SettingsPanel.tsx        # 设置面板
│   └── visual/                      # Visual Adapter 组件
│       ├── VisualAdapter.tsx
│       ├── WebBrowser.tsx
│       ├── IDE.tsx
│       └── ...
├── store/
│   └── useBlueprintStore.ts         # Zustand状态管理（未上传）
├── types/
│   └── index.ts                     # 类型定义（未上传）
└── lib/
    └── utils.ts                     # 工具函数
```

### 10.2 相关文档

- `Blueclaw_AI_Canvas_API_Specification.md` — 原版 API 规范
- `Blueclaw_AI_Integration_Guide.md` — 集成指南
- `WEEK19.5_INTERFACE_INTEGRATION.md` — 历史接口文档

---

*文档版本: v2.0*  
*更新日期: 2026-04-22*  
*对应前端代码: https://github.com/kperxianpe/buleclawv1-frontword*
