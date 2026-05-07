# Blueclaw v2.1 未开发功能清单

> 生成时间: 2026-04-29 02:55  
> 基于前后端代码审查 + 功能测试验证

---

## 一、执行蓝图 — 干预面板三选项（后端缺失）

### 现状

前端 `InterventionPanel.tsx` 已完整实现三个选项 UI，点击后调用 `onAction()`：

| 选项 | 前端回调 | 后端状态 |
|------|---------|---------|
| **继续执行** | `onAction('continue')` | ❌ 无 handler |
| **重新规划** | `onAction('newBranch', customInput)` | ❌ 无 handler |
| **完全停止** | `onAction('stop')` | ❌ 无 handler |

### 前端链路

```
ExecutionNode.tsx → handleIntervene() → interveneExecution(stepId)
  → BlueprintCanvas.tsx handleExecAction(action, customInput)
    → 仅更新前端 store 状态（setShowInterventionPanel: false）
    → 无 WebSocket 消息发送到后端
```

### 需要补的后端

1. **WebSocket 消息类型注册** — `backend/websocket/message_router.py` 需新增：
   - `execution.intervene` / `execution.intervene_continue`
   - `execution.intervene_replan`
   - `execution.intervene_stop`

2. **Handler 实现** — `backend/websocket/handlers/` 需新建或扩展：
   - `handle_execution_intervene_continue()` — 跳过当前步骤，标记为 `skipped`，继续执行后续步骤
   - `handle_execution_intervene_replan()` — 触发 thinking_engine 的 `replan_from_step()`，保留已完成步骤数据，重新生成后续 execution 蓝图
   - `handle_execution_intervene_stop()` — 终止当前 blueprint 执行，状态设为 `cancelled`，推送 `execution.cancelled`

3. **执行引擎支持** — `blueclaw/core/execution_engine.py`：
   - 支持 `skip_step()` — 跳过当前步骤，不执行但标记完成
   - 支持 `cancel_blueprint()` — 停止执行循环
   - 支持 `replan_from_step(step_id, reason)` — 截断蓝图，保留已完成步骤，重新规划后续

4. **状态同步** — `blueclaw/core/state_sync.py`：
   - 新增 `push_execution_step_skipped()`
   - 新增 `push_execution_cancelled()`
   - 新增 `push_execution_replan_triggered()`

---

## 二、内容蓝图 — 黄色方块/ToolDock 拖拽（完全缺失）

### 现状

前端 ToolDock.tsx 有 8 个预定义工具，支持拖拽到 VisualAdapter.tsx，创建 visNode。但**全部是前端本地行为**，不涉及后端通信。

### 前端链路

```
ToolDock.tsx → handleDragStart() → 序列化 ToolItem JSON
  → VisualAdapter.tsx handleDrop() → 创建 ReactFlow visNode（仅前端状态）
    → 点击 visNode → openItem() → 显示详情面板
      → "用于思考蓝图" / "用于执行蓝图" 按钮 → handleToolUse() → console.log() 仅此而已
```

### 完全缺失的后端

#### 1. 消息协议（零实现）

| 需要的消息类型 | 说明 |
|---------------|------|
| `tool.drag_start` | 用户开始拖拽工具 |
| `tool.dropped` | 工具被拖放到 vis-adapter 区域 |
| `tool.attach_to_step` | 将工具绑定到 execution 步骤 |
| `tool.detach_from_step` | 解除工具与步骤的绑定 |
| `tool.execute` | 触发工具实际执行 |
| `tool.list` | 获取可用工具列表（动态） |
| `tool.create` | 用户自定义创建新工具 |

#### 2. 数据模型（零实现）

```python
# 需要的后端数据结构
class ToolItem(BaseModel):
    id: str           # 工具唯一标识
    name: str         # 显示名称
    type: Literal['mcp', 'skill', 'adapter', 'file']
    color: str        # UI 颜色
    description: str
    config: dict      # 工具配置（API endpoint、参数模板等）
    content: Optional[str]  # 工具内容（代码、模板等）

class ContentBlueprint(BaseModel):
    task_id: str
    items: List[ToolItem]           # 已拖入 vis-adapter 的工具
    bindings: List[ToolBinding]     # 工具与 execution 步骤的绑定关系

class ToolBinding(BaseModel):
    tool_id: str
    step_id: str
    binding_type: Literal['input', 'output', 'transform']  # 工具在步骤中的角色
```

#### 3. 存储层（零实现）

- 没有 `ContentBlueprint` 的持久化存储
- 没有 `ToolItem` 的数据库表 / 内存存储
- 没有工具配置的版本管理

#### 4. 执行层（零实现）

前端看到的工具是"概念"，后端没有对应实际执行能力：

| 前端工具 | 需要什么后端能力 | 当前状态 |
|---------|-----------------|---------|
| Web Search | MCP 调用 / Browser Adapter | 有 WebAdapter，但无与 ToolItem 的绑定 |
| Code Runner | 沙箱执行环境 | ❌ 无 |
| Image Gen | 图像生成 API | ❌ 无 |
| Data Analysis | 数据分析引擎 | ❌ 无 |
| Document | 文档处理管道 | ❌ 无 |
| Tools | 通用工具箱 | ❌ 无 |
| AI Assist | LLM 调用封装 | 有 LLM，但无与 ToolItem 的绑定 |
| API Call | HTTP 请求模板 | ❌ 无 |

---

## 三、冻结功能（已打通）

### 状态: ✅ 前后端完整

```
前端: ExecutionNode.tsx → handleFreeze() → send('freeze_request')
  → 后端: _handle_freeze_request() → WebAdapter 截图 → push_freeze_confirmed()
    → 前端: FreezeOverlay.tsx 显示截图 + 标注面板
```

无需额外开发。

---

## 四、Auto-Select 开关（已打通）

### 状态: ✅ 前后端完整

| 端 | 实现 |
|---|------|
| 前端 | `InputScreen.tsx` checkbox → `useBlueprintStore` `autoSelect` → `task.start` 携带 `auto_select` |
| 后端 | `Task` dataclass `auto_select` → `TaskManager` 保存 → `ThinkingEngine` `get_task_auto_select()` + `should_auto_select()` |

无需额外开发。

---

## 五、Vis-Adapter 三模式切换（前端已实现）

### 状态: 🟡 前端完成，后端部分支持

| 模式 | 前端 | 后端 | 状态 |
|------|------|------|------|
| **画布** | VisualAdapter.tsx ReactFlow | 无 | 纯前端 |
| **Web** | LiveBrowser.tsx iframe 渲染 HTML | WebAdapter 截图 + HTML snapshot | ✅ 通 |
| **IDE** | LiveIDE.tsx 骨架（文件标签栏+代码区+运行按钮） | ❌ 无代码执行后端 | 仅 UI |

**IDE 模式需要补：**
- 代码编辑器后端（接收代码 → 执行 → 返回结果）
- 文件系统接口（读取/保存文件）
- 运行状态同步（编译中/运行中/已完成/报错）

---

## 七、执行蓝图 — ExecutionNode 展开子步骤预览（轻量方案，与内容蓝图规划绑定）

### 需求来源

用户确认：ExecutionNode 展开后需要显示"小步骤"，让用户知道大步骤内部 adapter 会做什么。但当前展开后只能看到 `description` + `result` + `error`，看不到执行过程。

### 设计原则

1. **静态展示** — 不是动态实时更新 adapter 动作，而是预先展示"这个大步骤包含哪些子动作"
2. **最轻量** — 不改后端数据结构，不改 adapter 执行流程，只改前端展示
3. **绑定内容蓝图** — 和内容蓝图一起规划，因为内容蓝图也需要展示"工具内部包含哪些步骤"

### 实现方案（前端）

```typescript
// ExecutionNode.tsx 展开区域新增
const getSubStepPreview = (step: ExecutionStep) => {
  const tool = step.tool || 'llm_generate';
  const previews: Record<string, string[]> = {
    'skill_search': [
      '1. 提炼搜索关键词',
      '2. 打开搜索引擎',
      '3. 获取搜索结果',
      '4. 整理输出',
    ],
    'adapter_web': [
      '1. 打开目标网页',
      '2. 定位页面元素',
      '3. 执行操作（点击/填写/截图）',
      '4. 返回操作结果',
    ],
    'llm_generate': [
      '1. 准备生成提示词',
      '2. 调用 LLM 生成内容',
      '3. 格式化输出',
    ],
    'skill_file': [
      '1. 定位文件路径',
      '2. 读取/写入内容',
      '3. 确认操作完成',
    ],
  };
  return previews[tool] || ['1. 准备执行', '2. 调用工具', '3. 处理结果', '4. 输出报告'];
};
```

### 展示位置

在 `ExecutionNode.tsx` 展开区域的 `<div className="p-3">` 内，新增一个"执行过程"区块：

```tsx
{/* 子步骤预览 */}
<div className="mt-2 pt-2 border-t border-gray-700/50">
  <p className="text-[9px] text-gray-500 mb-1">执行过程</p>
  <ul className="space-y-1">
    {getSubStepPreview(step).map((sub, idx) => (
      <li key={idx} className="text-[10px] text-gray-400 flex items-center gap-1">
        <span className="w-1 h-1 rounded-full bg-gray-600" />
        {sub}
      </li>
    ))}
  </ul>
</div>
```

### 为什么和内容蓝图一起规划

内容蓝图的核心也是"展示工具内部步骤"。两个功能共享同一套"步骤预览"概念：

| 功能 | 展示对象 | 展示内容 |
|------|---------|---------|
| ExecutionNode 子步骤预览 | 大步骤 | 内部 adapter 动作 |
| 内容蓝图 ToolItem 详情 | 工具 | 内部执行流程 |

**统一方案**：后端在生成 execution 蓝图时，给 `ExecutionStep.metadata.preview_substeps` 填充静态预览列表；前端统一渲染。内容蓝图复用同一套渲染组件。

### 工作量

- 前端：`ExecutionNode.tsx` 新增 15-20 行代码 → **很小**
- 后端（可选）：`create_blueprint()` 生成时填充 `metadata.preview_substeps` → **很小**
- 不改数据结构、不改 adapter 流程

### 优先级

**P2**（和 IDE 模式代码执行后端同级）— 体验优化项，非阻塞。

---

*文档版本: v1.1*  
*追加时间: 2026-04-29 17:45*  
*下次更新: 内容蓝图或子步骤预览有进展时追加*

| 优先级 | 功能 | 工作量 | 说明 |
|-------|------|--------|------|
| **P0** | 干预面板三选项后端 | 中 | 复用现有 execution_engine 和 state_sync 框架 |
| **P1** | IDE 模式代码执行后端 | 中 | 需要沙箱执行环境 |
| **P2** | 内容蓝图基础协议 | 大 | 需要设计完整的消息协议 + 数据模型 + 存储层 |
| **P3** | 内容蓝图工具执行层 | 大 | 每个工具需要独立的执行后端 |
| **P4** | 工具自定义创建（+按钮） | 小 | 前端已有 UI，后端需 `tool.create` handler |

---

*文档版本: v1.0*  
*下次更新: 每当未开发功能有进展时追加*
