# 前后端功能对接差距分析报告

> 分析范围：frontword/app (前端) vs blueclawv2 (后端)
> 分析日期：2026-04-04
> 原则：只分析，不对接

---

## 一、后端全部功能接口清单

### 1.1 WebSocket 消息接口（Core 引擎层）

| 消息类型（前端发→后端收） | 后端处理模块 | 状态 |
|------------------------|-------------|------|
| `task.start` | ThinkingEngine | **已对接** |
| `thinking.select_option` | ThinkingEngine | **已对接** |
| `thinking.custom_input` | ThinkingEngine | **已对接** |
| `thinking.confirm_execution` | ExecutionEngine | **已对接** |
| `execution.start` | ExecutionEngine | **已对接** |
| `execution.pause` | ExecutionEngine | **已对接** |
| `execution.resume` | ExecutionEngine | **已对接** |
| `execution.intervene` | ReplanEngine | **已对接** |
| `execution.cancel` | ExecutionEngine | **已对接** |
| `adapter.list` | AdapterManager | **已对接** |
| `adapter.execute` | AdapterManager | **已对接** |
| `adapter.attach_to_step` | AdapterManager | **已对接** |
| `adapter.detach_from_step` | AdapterManager | **已对接** |
| `adapter.enter_edit` | AdapterManager | **已对接** |

| 消息类型（后端发→前端收） | 发送模块 | 状态 |
|------------------------|---------|------|
| `task.started` | StateSyncManager | **已对接** |
| `thinking.node_created` | StateSyncManager | **已对接** |
| `thinking.option_selected` | StateSyncManager | **已对接** |
| `thinking.completed` | StateSyncManager | **已对接** |
| `thinking.execution_confirmed` | StateSyncManager | **已对接** |
| `execution.blueprint_loaded` | StateSyncManager | **已对接** |
| `execution.started` | StateSyncManager | **已对接** |
| `execution.step_updated` | StateSyncManager | **已对接** |
| `execution.paused` | StateSyncManager | **已对接** |
| `execution.resumed` | StateSyncManager | **已对接** |
| `execution.completed` | StateSyncManager | **已对接** |
| `execution.replanned` | StateSyncManager | **已对接** |
| `adapter.listed` | MessageRouter | **已对接** |
| `adapter.edit_mode_entered` | MessageRouter | **已对接** |
| `adapter.attached` | MessageRouter | **已对接** |
| `adapter.detached` | MessageRouter | **已对接** |
| `state.changed` | StateMachine | **未对接** |
| `push_intervention_needed` | StateSyncManager | **未对接** |

### 1.2 REST API 接口（IDE 层 — 新增）

| 功能域 | 端点 | 状态 |
|--------|------|------|
| **文件系统** | `GET /api/ide/fs/tree` | **未对接** |
| | `GET /api/ide/fs/read` | **未对接** |
| | `POST /api/ide/fs/write` | **未对接** |
| | `POST /api/ide/fs/create` | **未对接** |
| | `DELETE /api/ide/fs/delete` | **未对接** |
| | `POST /api/ide/fs/rename` | **未对接** |
| **代码执行** | `POST /api/ide/run/execute` | **未对接** |
| | `GET /api/ide/run/output` (SSE) | **未对接** |
| | `POST /api/ide/run/kill` | **未对接** |
| | `GET /api/ide/run/result` | **未对接** |
| **测试执行** | `POST /api/ide/test/run` | **未对接** |
| | `GET /api/ide/test/result` | **未对接** |
| **KimiCode** | `POST /api/ide/kimicode/chat` (SSE) | **未对接** |
| | `POST /api/ide/kimicode/generate` | **未对接** |
| | `POST /api/ide/kimicode/inline` | **未对接** |
| | `POST /api/ide/kimicode/diff` | **未对接** |
| | `GET /api/ide/kimicode/diff/preview` | **未对接** |
| | `POST /api/ide/kimicode/diff/apply` | **未对接** |
| | `POST /api/ide/kimicode/diff/discard` | **未对接** |
| | `GET /api/ide/kimicode/sessions` | **未对接** |
| **WebSocket IDE** | `WS /ws/ide` | **未对接** |

### 1.3 Adapter 层能力（执行层）

| 能力 | 模块 | 后端状态 | 前端对接状态 |
|------|------|---------|------------|
| Web 浏览器自动化 | `web/executor.py` | 真实 Playwright | **未对接** |
| Web 页面分析 | `web/analyzer.py` | 真实 DOM 提取 | **未对接** |
| Web 元素定位 | `web/locator.py` | 三层回退策略 | **未对接** |
| Web 干扰检测 | `web/distraction.py` | DOM+像素双检测 | **未对接** |
| Web 步骤验证 | `web/validator.py` | 6 种验证类型 | **未对接** |
| Web 自动恢复 | `web/recovery.py` | 重试+回退+回滚 | **未对接** |
| Web 并行执行 | `web/parallel.py` | DAG 拓扑分组 | **未对接** |
| Web 截图压缩 | `core/screenshot.py` | PNG→WebP (>100x) | **未对接** |
| Web Canvas 标记 | `web/visualization.py` | 红圈/进度条/遮罩 | **未对接** |
| IDE 代码分析 | `ide/analyzer.py` | Tree-sitter AST | **未对接** |
| IDE 架构规划 | `ide/planner.py` | 依赖图+拓扑排序 | **未对接** |
| IDE 边界检查 | `ide/boundary.py` | allow/deny/protected | **未对接** |
| IDE 代码模型 | `ide/codemodel.py` | Kimi API 调用 | **未对接** |
| IDE 沙盒验证 | `ide/sandbox.py` | 语法+测试+静态分析 | **未对接** |
| IDE Diff 应用 | `ide/applier.py` | Git 自动提交+回滚 | **未对接** |
| IDE 修改循环 | `ide/loop.py` | CodeModel→Sandbox→Apply | **未对接** |
| 操作记录 | `core/operation_record.py` | 截图+结果+状态快照 | **未对接** |
| 检查点恢复 | `core/checkpoint_v2.py` | 基于记录恢复 | **未对接** |
| Web 检查点 | `web/checkpoint.py` | DOM/Cookie/Storage | **未对接** |

---

## 二、前端全部功能组件清单

### 2.1 页面/视图层

| 组件 | 功能描述 | 数据来源 |
|------|---------|---------|
| `App.tsx` | 主应用壳（Header + BlueprintCanvas） | - |
| `BlueprintCanvas.tsx` | 主画布：Thinking 阶段 + Execution 阶段可视化 | `useBlueprintStore` |
| `InputScreen.tsx` | 用户输入任务界面 | 本地 state |
| `CompletionScreen.tsx` | 执行完成结果展示 | `useBlueprintStore` |
| `Header.tsx` | 顶部栏：阶段指示器 + 重置按钮 | `useBlueprintStore` |

### 2.2 节点组件

| 组件 | 功能描述 |
|------|---------|
| `nodes/ThinkingNode.tsx` | 思考选项节点（A/B/C + 自定义输入） |
| `nodes/ExecutionNode.tsx` | 执行步骤节点（状态/依赖/结果） |
| `nodes/SummaryNode.tsx` | 执行摘要节点 |
| `ExecutionNode/index.tsx` | 执行节点详情 + Adapter 挂载区 |
| `ExecutionNode/AdapterAttachments.tsx` | Adapter 拖拽挂载展示 |

### 2.3 面板组件

| 组件 | 功能描述 | 数据来源 |
|------|---------|---------|
| `panels/DetailPanel.tsx` | 步骤详情展示面板 | `useBlueprintStore` |
| `panels/InterventionPanel.tsx` | 干预操作面板（继续/分支/停止） | `useBlueprintStore` |
| `panels/SettingsPanel.tsx` | 画布配置面板（间距/背景/缩放） | `useBlueprintStore` |

### 2.4 可视化组件（visual/）

| 组件 | 功能描述 | 数据来源 | 对接状态 |
|------|---------|---------|---------|
| `visual/IDE.tsx` | VS Code 风格 IDE 界面 | **硬编码 mock 数据** | **未对接** |
| `visual/WebBrowser.tsx` | 浏览器模拟器 | **硬编码 mock 页面** | **未对接** |
| `visual/ToolDock.tsx` | 工具 Dock | 本地 state | **未对接** |
| `visual/ToolEditor.tsx` | 工具编辑器 | 本地 state | **未对接** |
| `visual/VisualAdapter.tsx` | Adapter 可视化容器 | 本地 state | **未对接** |
| `visual/VisualToolBar.tsx` | 可视化工具栏 | 本地 state | **未对接** |
| `visual/DropZone.tsx` | 拖拽放置区 | 本地 state | **未对接** |
| `visual/AdapterDefault.tsx` | 默认 Adapter 视图 | 本地 state | **未对接** |

### 2.5 Hooks

| Hook | 功能 | 通信方式 | 对接状态 |
|------|------|---------|---------|
| `useWebSocket.ts` | WebSocket 连接管理（重连/发送/接收） | WS `ws://localhost:8006` | **已对接** |
| `useTask.ts` | 任务生命周期：启动/思考/执行/干预/完成 | WS 消息 | **已对接** |
| `useRealtimeSync.ts` | `useTask` 与 `useBlueprintStore` 同步桥 | WS + Store | **部分对接** |
| `useAdapter.ts` | Adapter 列表/绑定/执行/编辑 | WS 消息 | **已对接** |
| `use-mobile.ts` | 移动端检测 | - | 纯前端 |

### 2.6 Store

| Store | 功能 | 数据来源 |
|-------|------|---------|
| `useBlueprintStore.ts` | Zustand：阶段/思考节点/执行步骤/干预/画布配置 | **mockEngine.ts（纯本地生成）** |

---

## 三、已对接功能详细说明

### 3.1 WebSocket 基础连接
```
前端: useWebSocket.ts / WebSocketContext.tsx
     ↕ ws://localhost:8006
后端: backend/websocket/server.py
```
- 自动重连机制（指数退避）
- JSON 消息格式 `{type, payload, timestamp, message_id}`

### 3.2 任务生命周期（Thinking → Execution）
```
前端: useTask.ts + useRealtimeSync.ts
     ↕ WS 消息
后端: blueclaw/core/{thinking_engine,execution_engine,state_sync}
```

完整消息流（已验证可工作）：
```
[前端] task.start {user_input}
  → [后端] thinking.node_created {node}
  → [前端] 展示选项 A/B/C

[前端] thinking.select_option {task_id, option_id}
  → [后端] thinking.option_selected / thinking.node_created
  → [前端] 更新节点状态，展示下一个问题

[前端] thinking.confirm_execution {task_id}
  → [后端] execution.blueprint_loaded {blueprint}
  → [前端] 渲染执行步骤 DAG

[前端] execution.start {blueprint_id}
  → [后端] execution.step_updated {step}
  → [前端] 更新步骤状态（running → completed/failed）

[前端] execution.intervene {action: 'replan'}
  → [后端] execution.replanned {new_steps}
  → [前端] 更新执行蓝图
```

### 3.3 Adapter 操作
```
前端: useAdapter.ts
     ↕ WS 消息
后端: blueclaw/adapter/manager.py
```

已对接消息：
- `adapter.list` → `adapter.listed`
- `adapter.attach_to_step` → `adapter.attached`
- `adapter.detach_from_step` → `adapter.detached`
- `adapter.enter_edit` → `adapter.edit_mode_entered`
- `adapter.execute`

---

## 四、未对接功能详细分析

### 4.1 【核心】IDE 工作区 ↔ 后端 REST API（全部未对接）

#### 4.1.1 文件树
| 前端现状 | 后端能力 | 差距 |
|---------|---------|------|
| `IDE.tsx` 使用硬编码 `DEFAULT_FILES`（src/components/app.tsx 等） | `FileService.list_tree()` + `GET /api/ide/fs/tree` | 前端从未调用 API，文件树是写死的 mock 数据 |

#### 4.1.2 文件读写
| 前端现状 | 后端能力 | 差距 |
|---------|---------|------|
| 代码区是 `<pre><code>` 只读展示，无编辑功能 | `FileService.read_file()` / `write_file()` | 前端不能编辑代码，也没有保存到后端的机制 |

#### 4.1.3 终端/代码执行
| 前端现状 | 后端能力 | 差距 |
|---------|---------|------|
| 终端输出是硬编码数组 `['$ npm run dev', '> vite', ...]` | `ProcessService.start()` + SSE `/api/ide/run/output` | 运行按钮触发本地 setState，没有真实执行任何命令 |

#### 4.1.4 KimiCode 嵌入
| 前端现状 | 后端能力 | 差距 |
|---------|---------|------|
| IDE 组件没有 KimiCode 面板 | `KimiCodeService` + `/api/ide/kimicode/*` | 前端完全没有 AI 辅助编程 UI |

### 4.2 【核心】Web 浏览器 ↔ 后端 WebAdapter（全部未对接）

| 前端现状 | 后端能力 | 差距 |
|---------|---------|------|
| `WebBrowser.tsx` 是纯 React 模拟（Bing 首页/骨架屏），iframe 都没有 | `WebAdapter` 真实 Playwright 操作 Chromium，每步截图+验证+恢复 | 前端展示的是假网页，后端操作的是真浏览器，两者完全隔离 |

关键未对接点：
- 后端 `WebExecutor.execute_step()` 生成 `OperationRecord`（包含 before/after 截图）
- 后端 `WebCheckpointManager` 保存 DOM/Cookie/Storage
- 后端 `CanvasMindVisualizer` 在浏览器注入进度条、红圈、干扰高亮
- **前端没有任何地方展示真实的浏览器截图**

### 4.3 【同步层】useBlueprintStore ↔ 后端 StateSync

| 前端现状 | 后端能力 | 差距 |
|---------|---------|------|
| `useBlueprintStore` 使用 `mockEngine.ts` 生成假数据 | `StateSyncManager` 推送真实事件 | `useRealtimeSync.ts` 虽然存在，但实际桥接逻辑不完整（直接赋值而非调用 store action），且 `BlueprintCanvas` 主要读取的是 store 而非 useTask |

具体问题：
1. `useRealtimeSync.ts` 第 87 行：`(store as any).thinkingNodes = thinkingNodes;` —— 这不是 Zustand 的响应式更新方式
2. `BlueprintCanvas.tsx` 没有直接使用 `useRealtimeSync`，而是直接使用 `useBlueprintStore`
3. 当 WebSocket 连接成功时，`useTask` 会收到真实数据，但 store 不会自动更新

### 4.4 【干预层】InterventionPanel ↔ 后端干预引擎

| 前端现状 | 后端能力 | 差距 |
|---------|---------|------|
| `InterventionPanel.tsx` 调用 `store.handleIntervention(action)`，在 store 里本地处理 | `AdapterReplanEngine` + `InterventionUI` 支持 retry/skip/replan/abort | 前端的干预是本地 mock，没有通过 WebSocket 发送干预选择到后端 |

### 4.5 【AI 层】前端没有 KimiCode UI

后端提供的 KimiCode 能力：
- 聊天对话（SSE 流式）
- 代码生成（完整函数/文件）
- 内联补全（Copilot 式）
- Diff 生成 → 预览 → 应用

前端现状：
- 没有任何 AI 面板或聊天窗口
- 没有代码补全提示
- 没有 Diff 预览组件

### 4.6 【测试层】前端没有测试 UI

后端提供的测试能力：
- `POST /api/ide/test/run` — 运行 pytest/unittest
- `GET /api/ide/test/result` — 获取测试结果（通过/失败/错误详情）

前端现状：
- IDE 组件里没有测试面板
- 没有测试运行按钮
- 没有测试结果展示

### 4.7 【WebSocket IDE 通道】`/ws/ide` 未使用

后端 `IDEWebSocketManager` 可广播：
- `fs.change` — 文件被外部修改
- `run.output` — 终端输出
- `test.progress` — 测试进度
- `kimicode.chunk` — Kimi 流式输出
- `error` — 错误通知

前端现状：
- WebSocket 只连接到 `/`（主通道），没有订阅 `/ws/ide`
- 前端没有处理上述消息类型的逻辑

### 4.8 【截图/可视化层】OperationRecord / Screenshot 未展示

后端每步操作都生成：
- `OperationRecord`（before_screenshot, after_screenshot, result, state_snapshot）
- `WebCheckpointManager` 保存页面 DOM/Storage/Cookie

前端现状：
- 没有操作历史查看界面
- 没有截图对比展示
- `VisualAdapter` / `VisualToolBar` 组件存在但内容需确认

### 4.9 【Adapter 可视化】Web 执行过程未可视化

后端 Web 执行时注入：
- 进度条（当前步骤/总步骤）
- 红圈脉冲标记（操作位置）
- 干扰元素黄色遮罩
- 检查点旗帜

前端现状：
- 前端 `visual/` 目录下有相关组件，但需要确认是否接收后端截图并展示

### 4.10 【Git 层】前端 Git 按钮未对接

后端能力：
- `IncrementApplier.git_status()` — Git 状态查询
- `ApplyResult.commit_hash` — 自动提交

前端现状：
- IDE 组件有 GitBranch 图标按钮，但无点击处理

---

## 五、未对接功能优先级矩阵

| 优先级 | 功能域 | 前端改动 | 后端改动 | 业务价值 |
|-------|--------|---------|---------|---------|
| **P0** | IDE 文件树 ↔ `/api/ide/fs/*` | 新增 API 调用 | 已就绪 | 高（IDE 基础） |
| **P0** | IDE 代码编辑 ↔ `/api/ide/fs/read+write` | 编辑器改为可编辑 | 已就绪 | 高（IDE 基础） |
| **P0** | IDE 终端 ↔ `/api/ide/run/*` | 终端对接 SSE | 已就绪 | 高（执行闭环） |
| **P1** | KimiCode 面板 ↔ `/api/ide/kimicode/*` | 新增 AI 面板 | 已就绪 | 高（核心卖点） |
| **P1** | WebBrowser ↔ WebAdapter 截图 | 浏览器改为展示截图 | 截图推送到前端 | 高（Web 闭环） |
| **P1** | Store ↔ useTask 真实同步 | 重构 useRealtimeSync | 无需改动 | 高（数据一致性） |
| **P2** | 测试面板 ↔ `/api/ide/test/*` | 新增测试 UI | 已就绪 | 中 |
| **P2** | Diff 预览/应用 UI | 新增 Diff 组件 | 已就绪 | 中 |
| **P2** | `/ws/ide` 实时通道 | 新增消息处理器 | 已就绪 | 中 |
| **P3** | 操作记录/截图历史 | 新增历史面板 | 已就绪 | 低 |
| **P3** | Git 状态展示 | 状态栏对接 | 已就绪 | 低 |

---

## 六、对接建议（只分析，不对接）

### 6.1 前端需要新增/修改的模块

1. **IDE 数据层**：创建 `services/ideApi.ts`，封装 `fetch('/api/ide/fs/*')`, `fetch('/api/ide/run/*')`, SSE 连接
2. **IDE Store**：创建 `useIDEStore.ts`，管理文件树、打开的标签页、终端输出
3. **代码编辑器**：将 `<pre><code>` 替换为 Monaco Editor 或 CodeMirror，支持语法高亮和编辑
4. **终端组件**：对接 SSE `/api/ide/run/output`，实时追加输出
5. **KimiCode 面板**：新增右侧边栏，包含聊天历史、输入框、生成/解释/补全按钮
6. **Diff 预览组件**：使用 `diff2html` 或自研，展示 unified diff
7. **WebBrowser 改造**：改为展示后端推送的截图（base64 或 URL）
8. **useRealtimeSync 修复**：改为调用 store 的 action 方法而非直接赋值

### 6.2 后端需要补充的模块

目前新增 REST API 骨架已就绪，但以下需要完善：
1. **主 FastAPI 入口**：需要一个 `main.py` 来 `register_ide_routes(app, workspace_path)`
2. **截图推送机制**：WebAdapter 执行截图后，需要推送到前端（通过 `/ws/ide` 或主 WS 通道）
3. **CORS 配置**：前端开发服务器（Vite @ 5173）需要跨域访问后端（8006）
4. **身份验证**：当前 API 没有鉴权

---

## 七、总结

**已对接（可用）**：
- WebSocket 基础连接 ✅
- 任务生命周期（Thinking → Execution）✅
- Adapter 列表/绑定/执行 ✅

**未对接（需要开发）**：
- IDE 全部 REST API（文件/执行/测试/KimiCode）❌
- Web 浏览器真实操作与截图展示 ❌
- 前端 Store 与后端真实数据同步 ❌
- AI 辅助编程面板 ❌
- 终端真实执行与 SSE 输出 ❌
- Diff 预览/应用 ❌
- 操作历史/截图查看 ❌
