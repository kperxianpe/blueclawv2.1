# Blueclaw AI Canvas — 完整产品文档 v3

---

## 产品定位

**Blueclaw AI Canvas** 是一个面向 AI 工作流的**可视化编排画布系统**，采用"思考 → 执行 → 内容"三层架构，将 AI 任务的决策过程（思考蓝图）、执行过程（执行蓝图）以及知识/工具的组织（内容蓝图）以可视化的方式呈现给用户。系统支持用户通过拖拽、选择、连线等直觉式操作与 AI 工作流进行交互，实现人机协同的任务编排。

**核心价值：** 让 AI 工作流"看得见、摸得着、改得了"，用户不再是黑盒的旁观者，而是工作流的共同设计者。

---

## 一、系统架构概览

```
Blueclaw AI Canvas — 三层架构

思考蓝图(左栏~31%)    工具栏(中栏)      执行区域(右栏~69%)
┌──────────────┐   ┌──────────┐   ┌──────────────────────────┐
│              │   │          │   │  执行蓝图(上)              │
│ ThinkingNode │   │ ToolDock │   │  (绿色·工作流)             │
│ (蓝色·决策树) │   │(黄色方块) │   │  主路径+分支+汇合           │
│              │   │ 可拖拽    │   │                          │
│ 四选一选项    │   │ 到思考/  │   ├──────────────────────────┤
│ 自定义输入    │   │ 执行/    │   │  AdapterViser(下)         │
│ 工具关联区    │   │ 画布     │   │  画布/Web/IDE/自定义        │
│              │   │          │   │  内容蓝图拖放+连线           │
└──────────────┘   └──────────┘   └──────────────────────────┘

FreezeOverlay(冻结)  InterventionPanel(干预)  SettingsPanel(设置)
Zustand Store(全局状态)  ContentBlueprintSystem(内容蓝图子系统)
```

---

## 二、文件结构与组件对应关系

### 根级文件

| 文件 | 职责 | 关联状态 |
|------|------|---------|
| `App.tsx` | 根组件：phase 状态机 + 四阶段条件渲染 + 面板挂载 | phase: 'input'|'thinking'|'execution'|'completed' |
| `main.tsx` | 入口：ReactDOM.createRoot + Tailwind CSS | — |
| `types/index.ts` | 全局类型：ThinkingNodeType, ExecutionStep, CanvasConfig | — |

### Store

| 文件 | 职责 | 核心 Actions |
|------|------|-------------|
| `store/useBlueprintStore.ts` | Zustand 全局状态 | startThinking, selectThinkingOption, completeThinking, executeNextStep, interveneExecution, handleIntervention, reset |

### Mock

| 文件 | 职责 | 输出 |
|------|------|------|
| `mock/mockEngine.ts` | 模拟数据引擎 | generateThinkingNode(index, question?) → 思考节点；generateExecutionBlueprint(spacing) → 9步骤执行蓝图 |

### 主组件

| 文件 | 职责 | 关联节点/Store |
|------|------|---------------|
| `components/BlueprintCanvas.tsx` | 主画布容器：左右分栏(thinking:execution) + 上下分栏(蓝图:AdapterViser) + ReactFlow 集成 | thinkingNodes[], executionSteps[] |
| `components/Header.tsx` | 顶部导航：Logo + 阶段指示器 + 操作按钮 | phase |
| `components/InputScreen.tsx` | 输入阶段：大号输入框 + "开始"按钮 | → startThinking() |
| `components/CompletionScreen.tsx` | 完成阶段：执行摘要 + "开始新任务" | → reset() |

### ReactFlow 自定义节点

| 文件 | 职责 | 主题色 | 关键特性 |
|------|------|--------|---------|
| `components/nodes/ThinkingNode.tsx` | 思考节点：四选一决策 | 蓝色 #3B82F6 | Handle id="top"/"bottom" + ToolBadgeMini + 自定义输入 |
| `components/nodes/ExecutionNode.tsx` | 执行节点：进度追踪 | 绿色 #10B981 | 状态色(pending灰/running蓝/completed绿/failed红) + 干涉按钮 |
| `components/nodes/SummaryNode.tsx` | 摘要节点：任务汇总 | 绿渐变 | 统计 + 步骤列表 |

### 内容蓝图系统（核心子系统）

| 文件 | 职责 | 关键导出 |
|------|------|---------|
| `components/visual/ContentBlueprintNode.tsx` | 内容蓝图节点：折叠/展开态 + 内部画布 + 单元管理 + 连线 | ContentUnit, ContentConnection, ContentBlueprint 接口 |
| `components/visual/VisualAdapter.tsx` | 多标签页容器 + 内容蓝图画布 + 拖放处理 | CanvasPage, ReactFlowProvider |
| `components/visual/ToolDock.tsx` | 工具侧边栏：10个预设工具 + 可拖拽 | ToolItem, ToolBlueprint, ToolBadge, ToolBadgeMini |
| `components/visual/ToolEditor.tsx` | 工具编辑弹窗：title/condition/media 编辑 | — |
| `components/visual/VisualToolBar.tsx` | 可视化工具栏 | — |
| `components/visual/AdapterDefault.tsx` | 默认Adapter标签页（任务进度面板） | — |
| `components/visual/WebBrowser.tsx` | Web浏览器模拟标签页（Edge风格） | — |
| `components/visual/IDE.tsx` | IDE模拟标签页（VSCode风格） | — |
| `components/visual/DropZone.tsx` | 拖放接收区域 | — |

### 面板系统

| 文件 | 职责 | 触发条件 |
|------|------|---------|
| `components/panels/FreezeOverlay.tsx` | 冻结覆盖层：截图 + 思考蓝图预览 | 点击"冻结"按钮 |
| `components/panels/InterferencePanel.tsx` | 干涉面板：齿轮按钮组（编辑/删除/关联） | 点击齿轮图标 |
| `components/panels/InterventionPanel.tsx` | 干预面板：继续执行/新分支/停止 | 步骤失败(step_003) |
| `components/panels/SettingsPanel.tsx` | 设置面板：比例/间距/主题(Unity风格) | 点击设置图标 |
| `components/panels/DetailPanel.tsx` | 节点详情面板 | 点击节点详情 |

---

## 三、四阶段工作流

### Phase 1: input → thinking
- **组件：** `InputScreen.tsx`
- **用户操作：** 输入自然语言需求 → 点击"开始"
- **Action：** `startThinking()` 生成第一个思考节点
- **→ Phase 2**

### Phase 2: thinking → execution
- **组件：** `BlueprintCanvas.tsx` + `ThinkingNode.tsx`
- **每轮：** 显示问题 + 选项A/B/C + 自定义输入
- **用户操作：** 选择选项或输入自定义内容
- **Action：** `selectThinkingOption()` → 生成下一节点（共3轮）
- **工具区：** ToolBadgeMini 小方块显示关联工具
- **→ Phase 3**（3轮后 `completeThinking()` 生成执行蓝图）

### Phase 3: execution → completed
- **组件：** `BlueprintCanvas.tsx` + `ExecutionNode.tsx`
- **布局：** 主路径水平 + 分支垂直 + 汇合节点
- **状态机：** pending → running → completed/failed
- **干预：** step_003 固定失败 → InterventionPanel（继续/新分支/停止）
- **→ Phase 4**（全部步骤完成）

### Phase 4: completed → input
- **组件：** `CompletionScreen.tsx`
- **显示：** 执行摘要统计
- **Action：** `reset()` → 返回 Phase 1

---

## 四、Zustand Store 完整规范

**文件：** `src/store/useBlueprintStore.ts`

### State 结构

```typescript
interface BlueprintState {
  // 阶段
  phase: 'input' | 'thinking' | 'execution' | 'completed'
  userInput: string

  // 思考蓝图
  thinkingNodes: ThinkingNodeType[]
  currentThinkingIndex: number       // 0~2, 最大3轮
  selectedThinkingNodeId: string | null

  // 执行蓝图
  executionSteps: ExecutionStep[]
  selectedExecutionStepId: string | null

  // 干预
  showInterventionPanel: boolean
  interventionStepId: string | null

  // 画布配置
  canvasConfig: {
    leftRightRatio: number           // 默认 2.236 (√5)
    execTopBottomRatio: number       // 默认 2
    nodeSpacing: number              // 默认 180
    theme: 'dark' | 'light'          // 默认 'dark'
  }
}
```

### Actions 完整列表

```typescript
// 阶段切换
startThinking: () => void                          // input → thinking, 生成首节点
completeThinking: () => void                       // thinking → execution, 生成执行蓝图
reset: () => void                                  // 重置所有状态到初始值

// 思考蓝图操作
selectThinkingOption: (nodeId, optionId) => void   // 选择选项, 生成下一节点
setCustomInput: (nodeId, input) => void            // 设置自定义输入
addThinkingNode: (node) => void                    // 手动添加思考节点
removeThinkingNode: (id) => void                   // 删除思考节点

// 执行蓝图操作
addExecutionStep: (step) => void                   // 添加执行步骤
removeExecutionStep: (id) => void                  // 删除执行步骤
updateExecutionStepStatus: (id, status) => void    // 更新步骤状态
setSelectedExecutionStepId: (id) => void           // 选中执行步骤

// 干预操作
interveneExecution: (stepId) => void               // 从失败点重新思考
handleIntervention: (action) => void               // 处理干预: 'continue'|'newBranch'|'stop'

// 画布配置
updateCanvasConfig: (config) => void               // 更新画布配置
resetCanvasConfig: () => void                      // 重置画布配置

// 内容蓝图关联（v2 新增）
addToolToThinkingNode: (nodeId, toolId) => void    // 关联工具到思考节点
removeToolFromThinkingNode: (nodeId, toolId) => void
addToolToExecutionStep: (stepId, toolId) => void   // 关联工具到执行步骤
removeToolFromExecutionStep: (stepId, toolId) => void
```

---

## 五、内容蓝图系统（Content Blueprint）

### 5.1 产品定位

内容蓝图是 Blueclaw AI Canvas 中用于**组织和编排知识/工具**的可视化容器。它采用知识图谱的方式，让用户将 MCP 工具、Skill 能力和纯内容以节点+连线的形式组织在一起，形成可复用的输入条件模板。内容蓝图可以被思考蓝图和执行蓝图引用，告诉它们在执行时应该使用哪些工具和内容。

**一句话描述：** 内容蓝图 = 知识图谱式的工具/内容组织器，是思考蓝图和执行蓝图的"输入条件说明书"。

### 5.2 拖入规则

| 工具类型 | 拖入后状态 | 可编辑性 | 标签显示 |
|----------|-----------|---------|---------|
| `mcp` | 内容蓝图节点 | **只读** | "mcp不可编辑" |
| `skill` | 内容蓝图节点 | **只读** | "skill不可编辑" |
| `file` | 内容蓝图节点 | **可编辑** | "+ 添加" / "Save" |
| `setting` | 内容蓝图节点 | **可编辑** | "+ 添加" / "Save" |

### 5.3 数据结构

```typescript
// 内容单元（内部节点）
interface ContentUnit {
  id: string;
  type: 'tool' | 'content' | 'nested';
  x: number; y: number;              // 内部绝对坐标
  // content 类型字段
  title?: string;
  text?: string;
  images?: string[];
  // tool 类型字段
  toolId?: string;
  toolColor?: string;
  toolName?: string;
  // nested 类型字段
  nestedBlueprintId?: string;
  nestedName?: string;
}

// 内容连线（内部连线）
interface ContentConnection {
  id: string;
  fromUnitId: string;
  toUnitId: string;
  label?: string;                     // 逻辑标注
}

// 内容蓝图（存储在 ToolItem.blueprint 中）
interface ContentBlueprint {
  title?: string;
  condition?: string;
  media?: { images: string[]; text: string };
  units?: ContentUnit[];
  connections?: ContentConnection[];
}

// 工具项（扩展）
interface ToolItem {
  id: string; name: string; icon: LucideIcon;
  color: string; description: string;
  type: 'mcp' | 'skill' | 'setting' | 'file';
  blueprint?: ContentBlueprint;       // 内容蓝图数据
}
```

### 5.4 内部画布架构

```
ContentBlueprintNode (540px × auto, 黄色边框)
│
├── 头部
│   ├── 图标 (点击 → ToolEditor 弹窗)
│   ├── 标题 + 只读/可编辑标签
│   └── 展开/折叠按钮
│
├── 折叠态 (190px 宽)
│   └── 标题 + 条件摘要 + 单元缩略 (4个小方块)
│
└── 展开态 (540px 宽)
    ├── 操作栏: "+ 添加" | "Save"
    └── 内部画布 (500 × 350 px)
        ├── SVG 连线层
        │   ├── 可见连线 (#FBBF24, 3px, 发光)
        │   ├── 端点圆点 (黄色 4px)
        │   ├── 标注文字 (深色背景 + 黄边框)
        │   └── 透明点击路径 (14px, 接收双击)
        └── 内容单元层 (absolute 定位)
            ├── tool: 彩色小方块 (48×36)
            ├── content: 文字卡片 (70×36+)
            └── nested: 虚线边框 + 链接图标
```

### 5.5 内部交互完整清单

| 操作 | 触发方式 | 效果 | 处理函数 |
|------|---------|------|---------|
| 添加单元 | 点击 "+ 添加" | 创建空 content → ringLayout | handleAddContent |
| 选中单元 | **单击** | 黄边高亮 + 放大110% | handleUnitClick |
| 创建连线 | 选中A → **单击** B | A→B 虚线连线 | handleUnitClick(选中态) |
| 取消选中 | 单击空白/已选中 | 取消高亮 | handleBgClick |
| 编辑连线 | **双击** 连线 | 弹出"编辑连线标注"模态框 | handleConnDblClick |
| 编辑单元 | **双击** content | 弹出编辑弹窗(图文) | handleUnitDblClick |
| 移动单元 | Shift + 拖拽 | 自由移动 | PointerDown/Move/Up |
| 嵌套蓝图 | 拖入其他蓝图 | 创建 nested 单元 | onDropNested |
| Save | 点击 "Save" | 保存到 node.data | handleSave → onSave |

### 5.6 环形布局算法

```typescript
const INNER_W = 500, INNER_H = 350;
const UNIT_W = 52, UNIT_H = 36;

function ringLayout(units: ContentUnit[]): ContentUnit[] {
  const cx = INNER_W / 2;           // 250
  const cy = INNER_H / 2;           // 175
  const r = Math.min(INNER_W, INNER_H) * 0.32;  // ~112

  return units.map((unit, i) => {
    const angle = (i / Math.max(units.length, 1)) * Math.PI * 2 - Math.PI / 2;
    return {
      ...unit,
      x: cx + r * Math.cos(angle) - UNIT_W / 2,
      y: cy + r * Math.sin(angle) - UNIT_H / 2,
    };
  });
}
```

所有单元均匀分布在以画布中心为圆心、半径约 112px 的圆上，从顶部（-PI/2）开始顺时针排列。

### 5.7 SVG 连线渲染策略（三层分离）

| 层 | 元素 | pointerEvents | 作用 |
|----|------|---------------|------|
| 底层 | 可见连线 (path, stroke=#FBBF24, 3px) | **none** | 纯视觉渲染 |
| 中层 | 端点圆点 (circle, r=4, fill=#FBBF24) | **none** | 连接点标记 |
| 上层 | 透明点击路径 (path, stroke=transparent, 14px) | **stroke** | 接收双击事件 |

事件处理：透明路径的 `onDoubleClick` 调用 `handleConnDblClick(conn)`，通过 `e.stopPropagation()` 防止冒泡到容器。

### 5.8 事件防冲突机制

内部画布容器 CSS 类：`nodrag nopan nowheel`

| 问题 | 解决方案 |
|------|---------|
| ReactFlow 将内部点击误识别为画布拖拽 | `className="nodrag"` 阻止 ReactFlow drag |
| ReactFlow 将内部滚轮误识别为画布缩放 | `className="nowheel"` 阻止滚轮事件 |
| 单元 onMouseDown 阻断外壳拖拽 | 改用 `onClick` 处理单元交互 |
| 连线双击被单元层遮挡 | SVG 透明路径在上层 (zIndex) + pointerEvents:stroke |

---

## 六、AdapterViser 多标签页系统

### 6.1 架构

**文件：** `src/components/visual/VisualAdapter.tsx`

```
VisualAdapter (多标签页容器)
│
├── Tab 栏: [Adapter] [Web] [IDE] [+]
│
├── AdapterDefault (默认标签)
│   └── 任务执行进度面板
│
├── WebBrowser (Web 标签)
│   └── Edge 风格浏览器模拟
│
├── IDE (IDE 标签)
│   └── VSCode 风格代码编辑器模拟
│
└── CanvasPage (画布标签)
    └── ReactFlow 画布 ← 内容蓝图节点渲染区域
```

### 6.2 内容蓝图拖放流程

```
ToolDock (侧边栏)
  │ onDragStart: dataTransfer.setData('application/json', itemJSON)
  ▼
CanvasPage (画布)
  │ 原生事件监听 (addEventListener capture)
  │ processDrop()
  ▼
VisualAdapter.handleAddNode()
  │ 1. isReadOnly = (item.type === 'mcp' || item.type === 'skill')
  │ 2. onSave = (units, connections) → 写入 node.data.blueprint
  │ 3. 创建 enrichedNode (data: { item, isReadOnly, onSave })
  ▼
setNodes(prev => [...prev, enrichedNode])
  ▼
ReactFlow 渲染 contentBlueprint 节点
  ▼
ContentBlueprintNode 接收 { item, isReadOnly, onSave }
```

### 6.3 各子组件说明

| 组件 | 文件 | 功能 | 输入 |
|------|------|------|------|
| VisualAdapter | VisualAdapter.tsx | Tab容器+状态管理 | activeTab, onTabChange |
| CanvasPage | VisualAdapter.tsx | ReactFlow画布+拖放 | nodes, edges, onAddNode |
| WebBrowser | WebBrowser.tsx | Edge风格浏览器 | url, onUrlChange |
| IDE | IDE.tsx | VSCode风格编辑器 | code, onCodeChange |
| AdapterDefault | AdapterDefault.tsx | 任务进度面板 | task, onTaskUpdate |
| ToolDock | ToolDock.tsx | 可拖拽工具列表 | tools, onToolClick, onToolDrag |
| ToolEditor | ToolEditor.tsx | 工具编辑弹窗 | tool, onSave |

---

## 七、执行引擎核心逻辑

### 7.1 步骤就绪判断

```
步骤就绪条件：
1. status === 'pending'
2. 无依赖 (dependencies.length === 0) 或 所有依赖 status === 'completed'
```

### 7.2 执行调度算法

```
executeNextStep():
  1. 找第一个就绪步骤 (findNextReadyStep)
  2. 若无 → 所有完成 → 触发完成回调
  3. 设置 status = 'running'
  4. 模拟执行 (setTimeout 1500ms)
  5. 执行完成 → status = 'completed' (90%概率) / 'failed' (10%概率)
  6. 若 failed → 显示干预面板 (interventionStepId = step.id)
  7. 递归调用 executeNextStep() (setTimeout 500ms)
```

### 7.3 干预流程

```
步骤失败
  │
  ▼
InterventionPanel 显示 (继续执行 / 新分支 / 停止)
  │
  ├── 继续执行 (continue) → 从失败步骤重新执行
  ├── 新分支 (newBranch)  → 从失败步骤的思考节点重新规划
  └── 停止 (stop)         → 停止执行，显示已完成结果
```

---

## 八、后端对接扩展指南

### 8.1 需要扩展的 Actions

| Action | 当前行为 | 后端对接后 |
|--------|---------|-----------|
| `startThinking` | mock 生成 | POST /api/thinking/start {userInput} |
| `selectThinkingOption` | mock 生成 | POST /api/thinking/select {nodeId, optionId} |
| `completeThinking` | mock 生成 | POST /api/thinking/complete {thinkingNodes} |
| `executeNextStep` | 模拟执行 | POST /api/execution/step {stepId} |
| `interveneExecution` | 本地状态 | POST /api/execution/intervene {stepId} |

### 8.2 WebSocket 实时推送

```typescript
// 连接
const ws = new WebSocket('wss://api.blueclaw.ai/ws/session/{sessionId}')

// 接收执行状态更新
ws.onmessage = (event) => {
  const { stepId, status, progress, result, error } = JSON.parse(event.data)
  useBlueprintStore.getState().updateExecutionStepStatus(stepId, status)
}
```

### 8.3 内容蓝图持久化

```typescript
// Save 时同步到后端
POST /api/blueprint/save {
  blueprintId: node.id,
  units: ContentUnit[],
  connections: ContentConnection[],
  toolId: item.id
}

// 加载时从后端获取
GET /api/blueprint/{blueprintId} → { units, connections }
```

---

## 九、已修复的 Bug 记录

| Bug | 根因 | 修复方案 |
|-----|------|---------|
| 思考蓝图连线消失 | Handle 缺少 id 属性，无法匹配 edges 中 sourceHandle/targetHandle | 添加 `id="top"` / `id="bottom"` |
| 画布拖放鼠标禁止 | ReactFlow pane 拦截拖放事件 | 原生事件监听 (addEventListener capture) + ReactFlow onDrop 冗余 |
| 内容蓝图展开后无法拖动 | 内部元素 stopPropagation 阻断 ReactFlow drag | 改用 onClick + nodrag nopan nowheel CSS 类 |
| 内容蓝图内部无法连线 | onMouseDown 与 ReactFlow drag 冲突 | 统一使用 onClick 处理单元交互 |
| 连线双击无反应 | pointerEvents 冲突 + 连线颜色太淡 | 三层 SVG 分离 + 亮色 #FBBF24 + 透明点击路径在上层 |
| 单元位置重叠 | ringLayout 条件 `unit.x!==0 \|\| unit.y!==0` 阻止新单元布局 | 删除条件，始终使用环形布局 |
| 节点展开被截断 | fitView 将画布平移到思考蓝图位置 | defaultViewport + onInit 强制重置视口 |
| 节点在画布右下角 | screenToFlowPosition 坐标转换 + fitView 冲突 | 固定 position {x:50, y:50} + setCenter 平移 |

---

## 十、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-04-20 | 初始版本：思考蓝图 + 执行蓝图 + 基础拖放 |
| v2.0 | 2026-04-24 | 内容蓝图系统：内部画布 + 单元管理 + 连线 + 标注 |
| v2.1 | 2026-04-25 | 修复拖放兼容性 + 思考蓝图连线 + 只读/可编辑区分 |
| v2.2 | 2026-04-26 | 增大画布 + 图文编辑 + mcp/skill 标签 + 保存持久化 |
| v3.0 | 2026-04-26 | 修复内部交互（onClick 重写）+ 连线可见性 + 环形布局 + 完整文档 |

---

**部署地址：** https://h3coh4yw3qj6i.ok.kimi.link
**技术栈：** React 18 + TypeScript + Vite + Tailwind CSS + ReactFlow v12 + Zustand + Lucide React
