# Blueclaw Frontend

React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui

## 项目结构

```
src/
├── components/
│   ├── BlueprintCanvas.tsx       # 主画布（ReactFlow 双画布）
│   ├── InputScreen.tsx           # 任务输入页
│   ├── Header.tsx                # 顶部导航栏
│   ├── RealtimeProvider.tsx      # WebSocket 消息处理器
│   ├── nodes/
│   │   ├── ThinkingNode.tsx      # 思考节点（A/B/C 选项选择）
│   │   ├── ExecutionNode.tsx     # 执行节点（含冻结按钮）
│   │   └── SummaryNode.tsx       # 摘要节点
│   ├── panels/
│   │   ├── InterventionPanel.tsx # 干预面板（失败/暂停时弹出）
│   │   ├── FreezeOverlay.tsx     # 冻结覆盖层（截图+标注）
│   │   ├── SettingsPanel.tsx     # 画布设置
│   │   └── DetailPanel.tsx       # 节点详情
│   └── visual/
│       ├── VisualAdapter.tsx     # 视觉层适配器
│       ├── ToolDock.tsx          # 工具栏
│       └── ToolEditor.tsx        # 工具编辑器
├── contexts/
│   └── WebSocketContext.tsx      # WebSocket 连接管理
├── store/
│   └── useBlueprintStore.ts      # Zustand 全局状态
├── types/
│   ├── index.ts                  # 核心类型（FreezeState, AnnotationBox）
│   └── websocket.ts              # WebSocket 消息类型
├── hooks/
│   └── useTask.ts                # 任务相关 hooks
└── App.tsx                       # 根组件
```

## 核心功能

### 1. 冻结 / 截图 / 标注（W2.5 + W3）

**触发冻结**：
- 执行阶段，点击任意 **运行中** 步骤节点上的 **"冻结"** 按钮
- 或外部通过 WebSocket 发送 `freeze_request`

**FreezeOverlay 交互**：
1. 接收 `freeze.confirmed` 消息 → 弹出覆盖层，显示 Base64 截图
2. 选择 **"框选标注"** 工具 → 在截图上拖拽画框
3. 底部文本框输入备注（可选）
4. 点击 **"提交并继续"** → 发送 `submit_annotation`（含 `boxes` 数组）

**状态管理**（`useBlueprintStore`）：
```typescript
freeze: {
  isFrozen: boolean;
  freezeToken: string | null;
  stepId: string | null;
  screenshot: string | null;  // base64 PNG
  annotations: AnnotationBox[];
}
screenshots: { stepId: string; image: string; timestamp: number }[];
```

### 2. WebSocket 消息处理（RealtimeProvider）

| 消息类型 | 处理逻辑 |
|---------|---------|
| `task.started` | 切换到 thinking 阶段 |
| `thinking.node_created` | 添加思考节点 |
| `execution.blueprint_loaded` | 加载执行蓝图 |
| `execution.step_started/completed` | 更新步骤状态 |
| `freeze.confirmed` | 打开 FreezeOverlay，保存 screenshot |
| `screenshot` | 添加到 screenshots 数组 |
| `status_update` | 根据 status 更新 UI |

### 3. 实时模式 vs Mock 模式

- **实时模式**（`isRealtimeMode = true`，WebSocket 连接成功）：所有状态从后端推送
- **Mock 模式**（未连接后端）：使用本地 mock 数据，完整 UI 演示

## 启动

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`

WebSocket 后端：`ws://localhost:8006/ws`

## 环境变量

```bash
# .env.local
VITE_WS_URL=ws://localhost:8006/ws
```
