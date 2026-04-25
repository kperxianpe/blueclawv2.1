# Blueclaw AI Canvas — 系统架构与功能文档 v2

---

## 一、系统概述

Blueclaw AI Canvas 是一个基于 React + TypeScript 构建的可视化 AI 交互画布系统。用户通过输入自然语言需求，系统依次进入**思考蓝图**（决策树）和**执行蓝图**（工作流图）两个核心阶段，配合内容蓝图（Content Blueprint）实现知识图谱式的工具/内容组织。

**技术栈：**
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- ReactFlow (@xyflow/react) v12 — 画布渲染引擎
- Zustand — 全局状态管理
- Lucide React — 图标库

---

## 二、文件结构与组件树

```
src/
├── App.tsx                          # 根组件，管理全局阶段切换
├── main.tsx                         # 入口文件，Provider 挂载
├── types/
│   └── index.ts                     # 全局类型定义（ThinkingNodeType, ExecutionStep 等）
├── store/
│   └── useBlueprintStore.ts         # Zustand 全局状态存储（Phase/Nodes/Steps/Config）
├── mock/
│   └── mockEngine.ts                # 模拟数据生成器（思考节点、执行蓝图）
├── hooks/
│   └── use-mobile.ts                # 移动端检测 Hook
├── lib/
│   └── utils.ts                     # 工具函数（cn 等）
├── components/
│   ├── BlueprintCanvas.tsx           # 主画布容器（集成 ReactFlow）
│   ├── Header.tsx                    # 顶部导航栏（阶段指示 + 操作按钮）
│   ├── InputScreen.tsx               # 输入阶段 — 用户初始输入界面
│   ├── CompletionScreen.tsx          # 完成阶段 — 执行结果展示
│   ├──
│   ├── nodes/                        # ReactFlow 自定义节点
│   │   ├── ThinkingNode.tsx          # 思考蓝图节点（蓝色主题，选项卡 + 工具区）
│   │   ├── ExecutionNode.tsx         # 执行蓝图节点（绿色主题，进度 + 干涉）
│   │   └── SummaryNode.tsx           # 执行摘要节点（汇总结果）
│   ├──
│   ├── visual/                       # 内容蓝图系统（核心子系统）
│   │   ├── VisualAdapter.tsx         # 多标签页适配器（画布/Web/IDE）
│   │   ├── ToolDock.tsx              # 工具侧边栏（可拖拽工具列表）
│   │   ├── ToolEditor.tsx            # 工具编辑弹窗（blueprint 编辑）
│   │   ├── ContentBlueprintNode.tsx  # 内容蓝图节点（黄色主题，内部画布）
│   │   ├── VisualToolBar.tsx         # 可视化工具栏
│   │   ├── AdapterDefault.tsx        # 默认适配器页面
│   │   ├── WebBrowser.tsx            # Web 浏览器模拟页
│   │   ├── IDE.tsx                   # IDE 模拟页
│   │   └── DropZone.tsx              # 拖放接收区域
│   ├──
│   ├── panels/                       # 面板系统
│   │   ├── DetailPanel.tsx           # 节点详情面板
│   │   ├── FreezeOverlay.tsx         # 冻结覆盖层（截图 + 思考蓝图预览）
│   │   ├── InterferencePanel.tsx     # 干涉面板（齿轮按钮组）
│   │   ├── InterventionPanel.tsx     # 干预面板（继续/分支/停止）
│   │   └── SettingsPanel.tsx         # 设置面板
│   └──
│   └── ui/                           # shadcn/ui 基础组件库
│       ├── button.tsx, dialog.tsx, input.tsx, ...
│       └── （共 40+ 个基础 UI 组件）
```

---

## 三、核心状态管理（Zustand Store）

**文件：** `src/store/useBlueprintStore.ts`

### 状态结构

```typescript
interface BlueprintState {
  phase: 'input' | 'thinking' | 'execution' | 'completed'  // 当前应用阶段
  userInput: string                                         // 用户输入文本
  thinkingNodes: ThinkingNodeType[]                         // 思考蓝图节点数组
  currentThinkingIndex: number                             // 当前思考层级
  selectedThinkingNodeId: string | null                    // 选中的思考节点
  executionSteps: ExecutionStep[]                          // 执行步骤数组
  selectedExecutionStepId: string | null                   // 选中的执行步骤
  showInterventionPanel: boolean                           // 是否显示干预面板
  interventionStepId: string | null                        // 当前干预步骤ID
  canvasConfig: CanvasConfig                               // 画布配置
}
```

### 核心 Actions

| Action | 功能 | 触发条件 |
|--------|------|---------|
| `startThinking()` | 开始思考阶段，生成第一个思考节点 | 用户点击"开始"按钮 |
| `selectThinkingOption(nodeId, optionId)` | 选择思考选项 | 用户点击选项A/B/C |
| `setCustomInput(nodeId, input)` | 设置自定义输入 | 用户输入自定义内容 |
| `completeThinking()` | 完成思考，进入执行阶段 | 3轮思考后自动触发 |
| `executeNextStep()` | 执行下一步骤 | 自动调度（依赖检查） |
| `interveneExecution(stepId)` | 干预执行（重新思考） | 步骤失败时 |
| `handleIntervention(action)` | 处理干预（continue/newBranch/stop） | 干预面板按钮点击 |
| `addToolToThinkingNode()` | 关联工具到思考节点 | 拖入工具小方块 |
| `addToolToExecutionStep()` | 关联工具到执行步骤 | 拖入工具小方块 |
| `updateCanvasConfig(config)` | 更新画布配置 | 设置面板操作 |

---

## 四、四阶段工作流

### Phase 1: input（输入阶段）
- **组件：** `InputScreen.tsx`
- **功能：** 用户输入自然语言需求
- **流向：** 点击"开始" → `startThinking()` → Phase 2

### Phase 2: thinking（思考阶段）
- **组件：** `BlueprintCanvas.tsx` + `ThinkingNode.tsx`
- **功能：** 
  - 显示思考节点（蓝色主题），每个节点包含问题 + 4个选项（A/B/C/自定义）
  - 节点间用虚线箭头连接（Handle id="top"/id="bottom"）
  - 展开后显示工具区域（ToolBadgeMini 小方块）
  - 选择后自动折叠，生成下一个思考节点
- **流向：** 3轮选择后 → `completeThinking()` → Phase 3

### Phase 3: execution（执行阶段）
- **组件：** `BlueprintCanvas.tsx` + `ExecutionNode.tsx`
- **功能：**
  - 显示执行步骤（绿色主题），主路径水平排列 + 分支垂直排列
  - 步骤状态：pending → running → completed/failed
  - 失败时显示干预面板（InterventionPanel）
  - 干涉按钮旁显示关联工具（ToolBadgeMini）
- **流向：** 全部完成 → `phase = completed` → Phase 4

### Phase 4: completed（完成阶段）
- **组件：** `CompletionScreen.tsx`
- **功能：** 显示执行结果摘要

---

## 五、内容蓝图系统（Content Blueprint）

### 5.1 概述

内容蓝图是黄色主题的可编辑/只读容器节点，用于组织工具（skill/mcp）和纯内容单元，支持知识图谱式的连线和嵌套。

**拖入规则：**
| 工具类型 | 拖入后状态 | 可编辑性 |
|----------|-----------|---------|
| mcp | 内容蓝图节点 | 只读（显示"mcp不可编辑"） |
| skill | 内容蓝图节点 | 只读（显示"skill不可编辑"） |
| file | 内容蓝图节点 | 可编辑 |
| setting | 内容蓝图节点 | 可编辑 |

### 5.2 数据结构

**文件：** `src/components/visual/ContentBlueprintNode.tsx`

```typescript
interface ContentUnit {
  id: string;
  type: 'tool' | 'content' | 'nested';
  x: number; y: number;               // 内部坐标（绝对定位）
  title?: string;                     // 内容单元标题
  text?: string;                      // 描述文字
  images?: string[];                  // 图片URL数组
  toolId?, toolColor?, toolName?;     // tool 类型字段
  nestedBlueprintId?, nestedName?;    // nested 类型字段
}

interface ContentConnection {
  id: string;
  fromUnitId: string;
  toUnitId: string;
  label?: string;                     // 逻辑标注（双击编辑）
}
```

### 5.3 内部画布架构

```
ContentBlueprintNode (540px 宽，黄色边框)
├── 头部（可点击展开/折叠）
│   ├── 图标（点击打开编辑弹窗）
│   ├── 标题 + 只读/可编辑标签
│   └── 展开/折叠按钮
│
├── 展开后：
│   ├── 操作栏
│   │   ├── "+ 添加" 按钮（添加空内容单元）
│   │   └── "Save" 按钮（保存到 node.data）
│   │
│   └── 内部画布（500×350 px）
│       ├── SVG 连线层（贝塞尔曲线，无箭头）
│       │   ├── 可见连线（#FBBF24，3px，发光效果）
│       │   ├── 端点圆点（黄色 4px）
│       │   └── 透明点击路径（14px宽，接收双击事件）
│       │
│       └── 内容单元层（absolute 定位）
│           ├── tool 单元：彩色小方块 + 名称
│           ├── content 单元：文字卡片 + 图片
│           └── nested 单元：虚线边框 + 链接图标
```

### 5.4 内部交互

| 操作 | 触发方式 | 效果 |
|------|---------|------|
| 添加内容单元 | 点击 "+ 添加" | 创建空 content 单元到环形布局 |
| 选中单元 | 单击单元 | 黄边高亮 + 放大 110% |
| 创建连线 | 选中A后单击B | A→B 虚线连线 |
| 编辑连线标注 | **双击连线** | 弹出"编辑连线标注"模态框 |
| 编辑内容单元 | 双击 content 单元 | 弹出编辑弹窗（标题/描述/图片URL） |
| 移动单元 | Shift+拖拽 | 自由移动位置 |
| 嵌套蓝图 | 拖入其他蓝图 | 创建 nested 类型单元 |
| Save | 点击 Save | 保存 units + connections 到 blueprint |

### 5.5 关键实现细节

**环形布局（ringLayout）：**
- 所有单元均匀分布在以画布中心为圆心、半径 ≈ 112px 的圆上
- 每次添加新单元时重新计算全部位置

**SVG 连线渲染：**
- 使用贝塞尔曲线（C 指令）
- 透明路径在上层（pointerEvents: stroke）捕获双击
- 可见路径在下层（pointerEvents: none）只负责显示
- 端点圆点使用 circle 元素标记连接点

**事件系统：**
- 内部画布容器：`className="nodrag nopan nowheel"` 阻止 ReactFlow 拖拽干扰
- 单元使用 `onClick` 而非 `onMouseDown`，避免阻断外壳拖拽
- 连线双击使用 SVG path 的 `onDoubleClick`，通过 `e.stopPropagation()` 防止冒泡

---

## 六、工具系统（ToolDock + ToolEditor）

### 6.1 工具数据结构

**文件：** `src/components/visual/ToolDock.tsx`

```typescript
interface ToolItem {
  id: string;
  name: string;
  icon: LucideIcon;
  color: string;              // 主题色（#F59E0B 黄/#EC4899 粉等）
  description: string;
  type: 'mcp' | 'skill' | 'setting' | 'file';
  blueprint?: ToolBlueprint;  // 内容蓝图数据
  connections?: ToolConnections;
}

interface ToolBlueprint {
  title: string;              // 目标形容
  condition: string;          // 判断条件形容
  media: { images: string[]; text: string };
  units?: ContentUnit[];      // 内容蓝图内部单元
  connections?: ContentConnection[];
}
```

### 6.2 预设工具列表

| 工具 | 类型 | 颜色 | 用途 |
|------|------|------|------|
| Web Search | mcp | #F59E0B 黄 | 网络搜索 |
| Code Runner | mcp | #8B5CF6 紫 | 代码执行 |
| Image Process | skill | #3B82F6 蓝 | 图像处理 |
| Data Analysis | skill | #EC4899 粉 | 数据分析 |
| Text Gen | skill | #10B981 绿 | 文本生成 |
| API Call | mcp | #06B6D4 青 | API调用 |
| File Manager | file | #FDE68A 浅黄 | 文件管理 |
| Document | file | #FDE68A 浅黄 | 文档处理 |
| Settings | setting | #94A3B8 灰 | 系统设置 |
| Custom Tool | skill | #F43F5E 红 | 自定义工具 |

### 6.3 组件关系

```
ToolDock.tsx                    # 侧边栏工具列表（可拖拽）
  ├── ToolBadge.tsx             # 完整工具卡片（图标+名称+颜色）
  ├── ToolBadgeMini.tsx         # 迷你方块（只显示颜色+hover tooltip）
  └── findToolById()            # 全局工具查找函数

ToolEditor.tsx                  # 编辑弹窗
  ├── 内容蓝图编辑区（title/condition/media）
  └── 关联工具管理

VisualAdapter.tsx               # 多标签页容器
  ├── CanvasPage (画布)         # ReactFlow + 内容蓝图节点
  ├── WebBrowser (Web)          # 浏览器模拟
  └── IDE (IDE)                 # 代码编辑器模拟
```

---

## 七、画布系统（ReactFlow 集成）

### 7.1 主画布

**文件：** `src/components/BlueprintCanvas.tsx`

- 集成 ReactFlow，管理 thinking/execution/summary 三种节点
- 使用 `fitView` 自动适配视口
- 自定义节点注册：`nodeTypes = { thinking: ThinkingNode, execution: ExecutionNode, summary: SummaryNode }`

### 7.2 内容蓝图画布

**文件：** `src/components/visual/VisualAdapter.tsx`

- 独立的 CanvasPage 组件（使用 ReactFlowProvider）
- `defaultViewport={{ x: 0, y: 0, zoom: 1 }}` 固定左上角原点
- `onInit` 回调强制重置视口
- 原生拖放事件监听（addEventListener 捕获阶段）

### 7.3 节点注册

```typescript
const nodeTypes: NodeTypes = {
  thinking: ThinkingNodeComponent,       // 蓝色
  execution: ExecutionNodeComponent,     // 绿色
  summary: SummaryNodeComponent,         // 汇总
  contentBlueprint: ContentBlueprintNodeComponent,  // 黄色
};
```

---

## 八、面板系统

### 8.1 冻结覆盖层（FreezeOverlay）
- 触发：点击"冻结"按钮
- 显示：当前思考蓝图的截图 + 迷你思考节点预览
- 用途：锁定当前状态，防止自动推进

### 8.2 干涉面板（InterferencePanel）
- 触发：点击齿轮按钮组
- 显示：操作按钮（编辑/删除/关联等）
- 位置：浮动在节点旁边

### 8.3 干预面板（InterventionPanel）
- 触发：执行步骤失败（step_003 固定失败）
- 选项：继续执行 / 新建分支 / 停止
- 流向：选择后进入 thinking 阶段重新规划

### 8.4 设置面板（SettingsPanel）
- 画布间距调节
- 节点大小设置
- 主题切换

---

## 九、模拟引擎（Mock Engine）

**文件：** `src/mock/mockEngine.ts`

- `generateThinkingNode(index, question?)` — 生成思考节点（含3个预设选项）
- `generateExecutionBlueprint(spacing)` — 生成执行蓝图（6步骤 + 3分支）
- 预设选项内容：旅行目的地选择（自然风光/城市探索/文化体验）等

---

## 十、数据流图

```
用户输入
  │
  ▼
App.tsx (phase 状态)
  │
  ├── input ──► InputScreen.tsx
  │
  ├── thinking ──► BlueprintCanvas.tsx + ThinkingNode.tsx
  │     │
  │     ├── 选项选择 ──► useBlueprintStore.selectThinkingOption()
  │     │                    │
  │     │                    ▼
  │     │              生成下一节点 / 完成思考
  │     │
  │     └── 工具拖入 ──► ToolDock (onDragStart)
  │                           │
  │                           ▼
  │                     ThinkingNode (onDrop) ──► addToolToThinkingNode()
  │
  ├── execution ──► BlueprintCanvas.tsx + ExecutionNode.tsx
  │     │
  │     ├── 自动执行 ──► executeNextStep() (依赖检查 + 状态机)
  │     │
  │     ├── 失败干预 ──► InterventionPanel ──► interveneExecution()
  │     │
  │     └── 工具拖入 ──► addToolToExecutionStep()
  │
  └── completed ──► CompletionScreen.tsx

内容蓝图（独立系统）
  │
  ├── 拖入画布 ──► VisualAdapter.tsx ──► handleAddNode() ──► contentBlueprint 节点
  │
  ├── 展开节点 ──► ContentBlueprintNode.tsx ──► InnerCanvas
  │       │
  │       ├── 添加单元 ──► handleAddContent() ──► ringLayout()
  │       │
  │       ├── 单击选中 ──► setSelectedUnitId()
  │       │
  │       ├── 单击另一单元 ──► 创建 ContentConnection
  │       │
  │       ├── 双击连线 ──► handleEditConnection() ──► 模态框
  │       │
  │       ├── 双击单元 ──► onEditUnit() ──► 编辑弹窗（图文）
  │       │
  │       ├── 嵌套拖放 ──► onDropNested() ──► nested 类型单元
  │       │
  │       └── Save ──► onSave() ──► 写入 node.data.blueprint
  │
  └── 编辑弹窗 ──► ToolEditor.tsx
```

---

## 十一、已知限制与注意事项

1. **mcp/skill 类型为只读**：拖入后不可编辑内部内容，只能查看
2. **内容蓝图位置固定**：拖入画布后位置为 `{x: 50, y: 50}`（画布坐标系）
3. **环形布局**：新单元会重新排列所有已有单元的位置
4. **连线无箭头**：设计为无方向性的知识图谱连线
5. **Shift+拖拽移动**：按住 Shift 键可拖拽内容单元改变位置
6. **保存后状态保留**：使用 useEffect 同步 blueprint 数据，折叠再展开状态不丢失

---

**文档版本：** v2.0
**最后更新：** 2026-04-26
**部署地址：** https://h3coh4yw3qj6i.ok.kimi.link
