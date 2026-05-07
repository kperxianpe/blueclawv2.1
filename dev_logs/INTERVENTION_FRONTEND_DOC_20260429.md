# 前端执行蓝图干预功能文档

> 生成时间: 2026-04-29 03:00  
> 基于前端源码 + 后端 handler 代码审查

---

## 一、功能入口

### 1. 触发方式

用户点击 **ExecutionNode（绿色执行节点）** 上的 **"重新规划"** 按钮触发干预：

```
ExecutionNode.tsx (展开状态)
  └─ 按钮行: [冻结] [重新规划]
      └─ 点击"重新规划" → handleIntervene()
```

### 2. 按钮显示条件

```typescript
const canIntervene = step.status === 'running' || step.status === 'failed' || step.status === 'pending';
```

只有 **执行中 / 失败 / 待执行** 的节点才显示"重新规划"按钮。

---

## 二、干预面板 UI — InterventionPanel.tsx

### 面板结构

```
┌─────────────────────────────────────┐
│  [图标] 需要干预                       │
│  "步骤名称" 执行失败/已暂停/执行中      │
├─────────────────────────────────────┤
│  当前步骤: "步骤名称"                 │
│  已耗时: 12.5s                        │
├─────────────────────────────────────┤
│  请选择处理方式:                      │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ [▶] 继续执行                │   │
│  │ 跳过当前步骤，继续后续执行    │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ [⎇] 重新规划                │   │
│  │ 从当前步骤后重新思考并生成新蓝图│ │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ [■] 完全停止                │   │
│  │ 终止当前任务执行              │   │
│  └─────────────────────────────┘   │
│                                     │
│  [取消]              [确认]        │
└─────────────────────────────────────┘
```

### 交互逻辑

1. **点击选项卡片** → 卡片高亮（红色边框）
2. **选择"重新规划"** → 底部展开文本输入框（可选填写调整方向）
3. **点击"确认"** → 触发 `onAction(action, customInput)`
4. **未选择时确认按钮 disabled**

---

## 三、三个按钮的前端处理链路

### 按钮 1: 继续执行

**前端调用链:**

```
InterventionPanel.tsx
  └─ onAction('continue')  // 无 customInput
      └─ BlueprintCanvas.tsx
          └─ handleExecAction('continue')
              ├─ 实时模式: 无 WebSocket 消息发送（后端缺失 continue handler）
              └─ 调用 handleIntervention('continue')
                  └─ useBlueprintStore.ts
                      └─ handleIntervention('continue')
```

**useBlueprintStore.ts 处理逻辑:**

```typescript
case 'continue':
  // 1. 将当前步骤标记为 completed
  executionSteps.map(s => 
    s.id === interventionStepId 
      ? { ...s, status: 'completed', needsIntervention: false, result: '已继续' }
      : s
  )
  // 2. 关闭面板
  showInterventionPanel: false
  interventionStepId: null
  // 3. 500ms 后调用 executeNextStep() 继续执行后续步骤
```

**效果:** 当前步骤被强制标记为完成，执行引擎继续执行下一个步骤。

---

### 按钮 2: 重新规划

**前端调用链 (实时模式):**

```
InterventionPanel.tsx
  └─ onAction('newBranch', customInput)
      └─ BlueprintCanvas.tsx
          └─ handleExecAction('newBranch', customInput)
              ├─ 实时模式 → 发送 WebSocket: execution.intervene
                  {
                    task_id,
                    blueprint_id,
                    step_id,
                    action: 'replan',
                    custom_input: customInput
                  }
              └─ 调用 handleIntervention('newBranch')
```

**后端 handler — `_handle_execution_intervene`:**

```python
if action == "replan":
    # 1. 获取蓝图
    blueprint = execution_engine.blueprints.get(blueprint_id)
    # 2. 取消旧蓝图执行（避免残留任务）
    execution_engine.cancel_execution(blueprint_id)
    # 3. 收集已完成步骤摘要
    completed_summaries = [f"{s.name}: {s.result}" for s in blueprint.steps if completed]
    # 4. 标记干预步骤及后续步骤为 DEPRECATED
    for s in blueprint.steps:
        if s.id >= step_id:
            s.status = StepStatus.DEPRECATED
            archived_ids.append(s.id)
    # 5. 获取原始任务输入
    original_input = task.user_input
    # 6. 重启思考流程
    new_root_node = await thinking_engine.restart_thinking_from_intervention(
        task_id, original_input, completed_summary, custom_input
    )
    # 7. 推送消息到前端
    await state_sync.push_execution_returned_to_thinking(task_id, archived_ids)
    await state_sync.push_thinking_node_created(task_id, new_root_node, is_root=True)
```

**useBlueprintStore.ts 处理逻辑 (非实时模式/Mock):**

```typescript
case 'newBranch':
  // 1. 在干预步骤后插入两个替代步骤
  const newBranchSteps = [
    {
      id: `new_${Date.now()}_1`,
      name: '替代方案A',
      description: '用户干预生成的新步骤',
      status: 'pending',
      dependencies: [interventionStepId],
      isMainPath: false,
    },
    {
      id: `new_${Date.now()}_2`,
      name: '替代方案B',
      description: '用户干预生成的新步骤',
      status: 'pending',
      dependencies: [interventionStepId],
      isMainPath: false,
    }
  ]
  // 2. 重组 executionSteps 数组
  executionSteps = [
    ...executionSteps.slice(0, stepIndex + 1),
    ...newBranchSteps,
    ...executionSteps.slice(stepIndex + 1)
  ]
  // 3. 标记干预步骤 needsIntervention: false
  // 4. 关闭面板，500ms 后 executeNextStep()
```

**效果:** 
- **实时模式**: 后端废弃旧步骤 → 重启 thinking → 前端回到思考阶段重新选择
- **Mock 模式**: 前端本地插入两个"替代方案"步骤

---

### 按钮 3: 完全停止

**前端调用链:**

```
InterventionPanel.tsx
  └─ onAction('stop')  // 无 customInput
      └─ BlueprintCanvas.tsx
          └─ handleExecAction('stop')
              ├─ 实时模式: 无 WebSocket 消息发送（后端缺失 stop handler）
              └─ 调用 handleIntervention('stop')
                  └─ useBlueprintStore.ts
                      └─ handleIntervention('stop')
```

**useBlueprintStore.ts 处理逻辑:**

```typescript
case 'stop':
  // 1. 设置整体阶段为 completed
  phase: 'completed'
  // 2. 关闭面板
  showInterventionPanel: false
  interventionStepId: null
```

**效果:** 任务被终止，界面回到完成状态（但 execution 步骤保留，不继续执行）。

---

## 四、前端干预状态管理

### useBlueprintStore.ts 中的干预相关状态

```typescript
interface BlueprintState {
  showInterventionPanel: boolean;      // 面板是否显示
  interventionStepId: string | null;   // 当前干预的步骤 ID
}
```

### 干预相关方法

| 方法 | 作用 | 位置 |
|------|------|------|
| `interveneExecution(stepId)` | 打开干预面板，设置干预步骤 | useBlueprintStore.ts |
| `handleIntervention(action, customInput?)` | 处理三个选项的点击 | useBlueprintStore.ts |
| `hideIntervention()` | 关闭面板（不执行操作） | useBlueprintStore.ts |

---

## 五、前后端交互矩阵

| 按钮 | 前端 action | WebSocket 消息 | 后端 handler | 后端执行引擎方法 | 状态 |
|------|------------|----------------|-------------|-----------------|------|
| **继续执行** | `continue` | ❌ 无 | ❌ 无 | ❌ 无 skip_step() | **未打通** |
| **重新规划** | `newBranch` | ✅ `execution.intervene` (action='replan') | ✅ `_handle_execution_intervene` | ✅ `handle_intervention()` → `_replan_from_step()` | ✅ **已打通** |
| **完全停止** | `stop` | ❌ 无 | ❌ 无 | ❌ 无 cancel_blueprint() | **未打通** |

---

## 六、关键发现

### 1. "重新规划"是唯一打通后端的功能

只有 **重新规划** 按钮在实时模式下会发送 WebSocket 消息到后端，后端有完整的处理链路（cancel → archive → replan → push messages）。

### 2. "继续执行"和"完全停止"是前端本地行为

这两个按钮在实时模式下**不会发送任何 WebSocket 消息**，后端不知道用户点击了它们。所有处理都在前端 store 中完成。

### 3. 后端 action 命名不一致

前端使用的 action 名称 vs 后端支持的 action:

| 前端按钮 | 前端 action | 后端支持 action |
|---------|------------|----------------|
| 继续执行 | `continue` | `skip` (后端), `retry` |
| 重新规划 | `newBranch` | `replan` ✅ |
| 完全停止 | `stop` | 无对应 |

### 4. 后端 execution_engine.handle_intervention 支持 5 种 action

```python
action = "retry"     # 重试当前步骤
action = "skip"      # 跳过当前步骤 → 对应"继续执行"
action = "replan"    # 重新规划 → 对应"重新规划"
action = "modify"    # 修改方向
action = "change_tool"  # 更换工具
```

但前端只暴露了 3 个选项，且只有 "replan" 被正确映射。

---

## 七、需要修复的问题

| 问题 | 位置 | 修复方案 |
|------|------|---------|
| "继续执行"未发送 WebSocket | BlueprintCanvas.tsx handleExecAction | 实时模式下发送 `execution.intervene` (action='skip') |
| "完全停止"未发送 WebSocket | BlueprintCanvas.tsx handleExecAction | 实时模式下发送新消息类型（如 `execution.cancel`）或映射到现有 action |
| 前端 action 命名与后端不一致 | InterventionPanel.tsx / BlueprintCanvas.tsx | 统一命名：`continue` → `skip`，`newBranch` → `replan`，`stop` → `cancel` |
| 后端无 cancel_blueprint() 方法 | execution_engine.py | 添加方法或复用现有逻辑终止执行循环 |

---

## 八、相关文件清单

| 文件 | 职责 |
|------|------|
| `frontend/src/components/nodes/ExecutionNode.tsx` | 显示"重新规划"按钮，触发 interveneExecution() |
| `frontend/src/components/panels/InterventionPanel.tsx` | 干预面板 UI，三个选项卡片 |
| `frontend/src/components/BlueprintCanvas.tsx` | handleExecAction() — 分发三个选项的处理 |
| `frontend/src/store/useBlueprintStore.ts` | handleIntervention() — 实际处理干预逻辑 |
| `frontend/src/hooks/useTask.ts` | interveneExecution() — 实时模式发送 WebSocket |
| `backend/websocket/message_router.py` | `_handle_execution_intervene()` — 后端 handler |
| `blueclaw/core/execution_engine.py` | `handle_intervention()`, `_replan_from_step()`, `cancel_execution()` |
| `blueclaw/core/state_sync.py` | `push_execution_returned_to_thinking()`, `push_execution_replanned()` |

---

*文档版本: v1.0*  
*下次更新: 修复干预面板前后端一致性后*
