# Blueclaw v2.5 Adapter Interface Protocol

**版本**: v2.5.0  
**日期**: 2026-04-20  
**状态**: Week 30.6-31 执行基线  

---

## 1. 核心定义

### 1.1 Adapter 是什么

**Adapter = Agent 的可视化工作室**

- 一个**执行蓝图（ExecutionBlueprint）**在执行期间**只对应一个** Adapter
- 一个**Adapter**可以作为工作室被**多个执行蓝图复用**（串行，非并行）
- Adapter 内部包含：Skill（工具）、工作流（Blueprint）、工作器材（Web/IDE/Canvas 控制器）
- Agent 在 Adapter 中工作时**始终可视**：运行时状态、标注、冻结、干预全部在该工作室呈现

### 1.2 与旧概念的对照

| 旧概念（Week 21） | 旧概念（Week 30.5） | v2.5 统一概念 |
|------------------|-------------------|--------------|
| Adapter（元工具） | Adapter（运行时视图） | **Adapter（可视化工作室）** |
| `adapter.attach_to_step` | `adapter.action` | `adapter.blueprint.attach` + `adapter.runtime.action` |
| `adapter.execute` | `adapter.state_changed` | `adapter.runtime.start` + `adapter.runtime.state` |
| `useAdapter.ts` | `useAdapterAgent.ts` | **`useAdapterRuntime.ts`** |

---

## 2. 命名空间设计

所有接口统一在 `adapter.` 前缀下，分为三大子空间：

```
adapter.               ← 根命名空间
├── studio.*           ← 工作室管理（CRUD）
├── blueprint.*        ← 蓝图绑定（生命周期关联）
└── runtime.*          ← 运行时控制 + 事件推送
```

### 2.1 studio.* — 工作室管理

| 消息类型 | 方向 | 说明 |
|---------|------|------|
| `adapter.studio.list` | C→S | 列出所有工作室 |
| `adapter.studio.listed` | S→C | 返回工作室列表 |
| `adapter.studio.create` | C→S | 创建工作室 |
| `adapter.studio.created` | S→C | 创建成功 |
| `adapter.studio.get` | C→S | 获取详情 |
| `adapter.studio.detail` | S→C | 返回详情 |
| `adapter.studio.update` | C→S | 更新工作室 |
| `adapter.studio.updated` | S→C | 更新成功 |
| `adapter.studio.delete` | C→S | 删除工作室 |
| `adapter.studio.deleted` | S→C | 删除成功 |
| `adapter.studio.clone` | C→S | 克隆工作室 |
| `adapter.studio.cloned` | S→C | 克隆成功 |
| `adapter.studio.enter_edit` | C→S | 进入嵌套编辑 |
| `adapter.studio.edit_mode_entered` | S→C | 返回 blueprint 详情 |

**兼容说明**：`adapter.list` / `adapter.create` / `adapter.get` / `adapter.update` / `adapter.delete` / `adapter.clone` / `adapter.enter_edit` 作为 `adapter.studio.*` 的**别名保留**，后端同时支持两种写法，前端逐步迁移到 `adapter.studio.*`。

### 2.2 blueprint.* — 蓝图绑定

| 消息类型 | 方向 | 说明 |
|---------|------|------|
| `adapter.blueprint.attach` | C→S | 将执行蓝图绑定到工作室 |
| `adapter.blueprint.attached` | S→C | 绑定成功广播 |
| `adapter.blueprint.detach` | C→S | 解绑 |
| `adapter.blueprint.detached` | S→C | 解绑成功广播 |

**Payload 格式（attach）**：
```json
{
  "task_id": "task_xxx",
  "blueprint_id": "bp_xxx",
  "studio_id": "studio_xxx",
  "adapter_type": "web" | "ide" | "canvas" | "default"
}
```

### 2.3 runtime.* — 运行时控制 + 事件

**控制类（Client → Server）**：

| 消息类型 | 说明 |
|---------|------|
| `adapter.runtime.start` | 启动工作室运行 |
| `adapter.runtime.pause` | 暂停 |
| `adapter.runtime.resume` | 恢复 |
| `adapter.runtime.freeze` | 冻结（人工干预）|
| `adapter.runtime.unfreeze` | 解除冻结 |
| `adapter.runtime.retry` | 重新执行当前步骤 |
| `adapter.runtime.replan` | 重新规划后续步骤 |
| `adapter.runtime.dismiss_annotation` | 前端 dismiss 一条标注 |

**事件类（Server → Client）**：

| 消息类型 | 说明 |
|---------|------|
| `adapter.runtime.state` | 状态变更推送 |
| `adapter.runtime.annotated` | 标注推送 |
| `adapter.runtime.frozen` | 冻结事件 |
| `adapter.runtime.unfrozen` | 解除冻结事件 |
| `adapter.runtime.completed` | 运行完成 |
| `adapter.runtime.error` | 运行时错误 |

**Payload 格式（state 事件）**：
```json
{
  "task_id": "task_xxx",
  "blueprint_id": "bp_xxx",
  "studio_id": "studio_xxx",
  "step_id": "step_xxx",
  "state": "running" | "paused" | "frozen" | "error" | "idle",
  "current_url": "https://...",
  "current_file": "src/App.tsx",
  "annotations": [
    {
      "id": "ann_001",
      "level": "error" | "warning" | "info" | "freeze",
      "message": "Selector not found",
      "rect": {"x": 100, "y": 200, "width": 50, "height": 30}
    }
  ],
  "timestamp": 1776617239470
}
```

---

## 3. 生命周期状态机

```
                    ┌─────────────┐
    blueprint.attach│             │
         ──────────►│    idle     │
                    │             │
                    └──────┬──────┘
                           │ runtime.start
                           ▼
                    ┌─────────────┐
                    │  connecting │
                    │  (准备环境)  │
                    └──────┬──────┘
                           │ 环境就绪
                           ▼
    ┌──────────┐    ┌─────────────┐    ┌──────────┐
    │  paused  │◄───│   running   │───►│  error   │
    │ (可恢复)  │    │  (执行中)   │    │ (需干预)  │
    └────┬─────┘    └──────┬──────┘    └────┬─────┘
         │                 │                 │
         │ runtime.resume  │ runtime.freeze  │ runtime.retry
         └────────────────►│                 │
                           ▼                 │
                    ┌─────────────┐          │
                    │   frozen    │◄─────────┘
                    │  (人工冻结)  │
                    └──────┬──────┘
                           │ runtime.unfreeze
                           ▼
                    ┌─────────────┐
                    │  completed  │
                    │  (运行完成)  │
                    └─────────────┘
```

---

## 4. 与 IDE REST API 的关系

| 层 | 协议 | 端口 | 用途 |
|---|------|------|------|
| Adapter Runtime | WebSocket (`/ws`) | 8006 | 实时状态推送 + 干预 |
| IDE Studio | HTTP REST (`/api/ide/*`) | 8006 | 文件系统、代码执行、AI 对话 |
| IDE Studio | WebSocket (`/ws/ide`) | 8006 | IDE 实时推送（fs.change / run.output）|

**统一入口**：后端使用 FastAPI + Uvicorn 启动，同时承载 HTTP REST 和 WebSocket。

前端连接：
- `ws://localhost:8006/ws` → 主 WebSocket（任务生命周期 + adapter runtime）
- `ws://localhost:8006/ws/ide` → IDE 专用 WebSocket
- `http://localhost:8006/api/ide/*` → IDE REST API

---

## 5. 前端 Hook 统一设计

**合并 `useAdapter.ts` + `useAdapterAgent.ts` → `useAdapterRuntime.ts`**

```typescript
interface UseAdapterRuntimeReturn {
  // === Studio 管理（原 useAdapter CRUD）===
  studioList: AdapterStudio[];
  isLoading: boolean;
  fetchStudios: () => void;
  createStudio: (data: StudioCreateData) => void;
  updateStudio: (id: string, data: Partial<StudioCreateData>) => void;
  deleteStudio: (id: string) => void;
  cloneStudio: (id: string, newName?: string) => void;
  enterEditMode: (id: string) => void;
  exitEditMode: () => void;
  editMode: { studioId: string; name: string; blueprint: any } | null;

  // === Blueprint 绑定 ===
  currentStudioId: string | null;
  attachToBlueprint: (blueprintId: string, studioId: string, type: AdapterType) => void;
  detachFromBlueprint: (blueprintId: string) => void;

  // === Runtime 状态（原 useAdapterAgent）===
  runtimeState: AdapterState;
  annotations: Annotation[];
  currentUrl?: string;
  currentFile?: string;

  // === Runtime 操作 ===
  startRuntime: () => void;
  pauseRuntime: () => void;
  resumeRuntime: () => void;
  freeze: () => void;
  unfreeze: () => void;
  retry: () => void;
  replan: () => void;
  dismissAnnotation: (id: string) => void;
}
```

**Store 合并**：`useAdapterStore` 同时存储 studioList + runtimeState，避免状态分散。

---

## 6. 向后兼容策略

| 旧消息类型 | 新消息类型 | 后端处理 |
|-----------|-----------|---------|
| `adapter.list` | `adapter.studio.list` | 别名，同 handler |
| `adapter.create` | `adapter.studio.create` | 别名，同 handler |
| `adapter.get` | `adapter.studio.get` | 别名，同 handler |
| `adapter.update` | `adapter.studio.update` | 别名，同 handler |
| `adapter.delete` | `adapter.studio.delete` | 别名，同 handler |
| `adapter.clone` | `adapter.studio.clone` | 别名，同 handler |
| `adapter.enter_edit` | `adapter.studio.enter_edit` | 别名，同 handler |
| `adapter.attach_to_step` | `adapter.blueprint.attach` | **废弃**，逐步迁移 |
| `adapter.detach_from_step` | `adapter.blueprint.detach` | **废弃**，逐步迁移 |
| `adapter.execute` | `adapter.runtime.start` | **废弃**，逐步迁移 |
| `adapter.execution_started` | `adapter.runtime.state` | 替换为统一 state 事件 |
| `adapter.execution_completed` | `adapter.runtime.completed` | 保留，语义不变 |

---

*Protocol v2.5.0 — Week 30.6-31 执行基线*
