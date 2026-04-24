# API Changelog

> 本文档记录 Blueclaw V2 接口的所有变更。  
> 权威规范: `api_specification_unified.md`（`api_specification.md` 已被取代，降级为历史规范）

---

## 2026-04-23 — 接口层统一

### 规范统一
- **命名规范**: 统一为点号分隔消息类型 + 下划线字段
  - `thinking_node_added` → `thinking.node_created`
  - `nodeId` → `current_node_id`
  - `optionId` → `option_id`
- **废弃 V2 的 `phase_change` 事件**: 改为由 `task.started` + `execution.blueprint_loaded` 隐含推断 phase
- **WebSocket 路径统一**: `/ws/blueprint` → `/ws`（对齐后端实际运行路径）
- **API_INTERFACE_V2.md 降级**: 标记为"前端设计愿景参考"，非运行时规范

### 文档新增
- `api_specification_unified.md` — **唯一权威运行时接口规范** ⭐
- `api_specification.md` — 历史运行时规范（已被 unified 取代）
- `API_INTERFACE_V2.md` — 前端设计愿景（非权威）
- `interface_comparison_report.md` — 历史对比分析（记录当时决策背景）
- `api_changelog.md` — 本文档

### Week 1 完成（2026-04-23）
- [x] HEC 自愈控制器: `blueclaw/adapter/hec.py`
- [x] StateSync 补齐: `push_screenshot`, `push_status_update`, `push_freeze_confirmed`, `push_replan_result`
- [x] Message Router 新 handler: `freeze_request`, `submit_annotation`, `retry_step`, `request_replan`, `confirm_replan`
- [x] AdapterManager 增强: `screenshot()` + `task_id→adapter_type` 映射
- [x] ExecutionEngine 对接: `_maybe_capture_screenshot()` 钩子

### Week 2 完成（2026-04-23）
- [x] 前端双模式改造: ExecutionNode/DetailPanel/BlueprintCanvas 干预/冻结动作支持 WS
- [x] 后端 5 个干预 handler 业务逻辑补齐:
  - `freeze_request` → 截图 + 冻结 runtime + 推送 `freeze.confirmed`
  - `submit_annotation` → 解冻 runtime + 恢复 ExecutionEngine + 推送状态更新
  - `retry_step` → `ExecutionEngine.handle_intervention("retry")` + annotation + 状态推送
  - `request_replan` → `ExecutionEngine.handle_intervention("replan")` + 推送 `replan.result`
  - `confirm_replan` → accept 恢复执行 / reject 保持 paused + 状态推送

### Week 2.5 E2E 验证完成（2026-04-24）
- [x] **方向 A：干预链路验证** — `freeze_request` → `freeze.confirmed(screenshot=True)` → `submit_annotation` → `status_update` ✅ 5/5
- [x] **方向 B：浏览器执行验证** — Playwright Chromium 自动启动，步骤执行后自动截图推送 ✅ 9/9, 3 screenshots
- [x] **方向 C：标注回传验证** — `submit_annotation` payload 含 boxes 坐标，后端接收并返回确认 ✅
- [x] **修复 ExecutionEngine 截图逻辑**:
  - `state_sync` 未定义 → 添加延迟导入
  - WebAdapter 未自动初始化 → `_maybe_capture_screenshot` + `_execute_blueprint` 自动 init
  - WebAdapter 过早清理 → 移除 finally 中 cleanup，避免 freeze_request 时浏览器已关闭
- [x] **修复 message_router freeze_request 截图逻辑**:
  - `AdapterManager` 实例不一致 → handler 内部自动初始化 WebAdapter

### 已知缺口（待补齐）
- [ ] 截图框: `add_screenshot_box` / `select_mini_option`（前端 FreezeOverlay 功能）
- [ ] 视觉系统补档: `vis_*` 系列接口文档化
- [ ] ExecutionEngine-Adapter 深度对接: Web 步骤真实浏览器执行
- [ ] 干预/冻结功能完整 E2E 验证

---

## 消息类型变更记录

### 前端 → 后端 (Client → Server)

| 消息类型 | 变更 | 说明 | 状态 |
|---------|------|------|------|
| `user_input` | 不变 | V2 适配层已支持 | ✅ 已验证 |
| `select_option` | 不变 | V2 适配层自动转换字段名 | ✅ 已验证 |
| `custom_input` | 不变 | V2 适配层自动转换字段名 | ✅ 已验证 |
| `execution.start` | 不变 | 启动执行蓝图 | ✅ 代码有 |
| `execution.pause` | 不变 | 暂停执行 | ✅ 代码有 |
| `execution.resume` | 不变 | 恢复执行 | ✅ 代码有 |
| `execution.cancel` | 不变 | 取消执行 | ✅ 代码有 |
| `execution.intervene` | 不变 | 执行干预 | ✅ 代码有 |
| `vis.preview` | 新增文档 | 视觉预览 | ⚠️ 未文档化 |
| `vis.user_selection` | 新增文档 | 视觉选择 | ⚠️ 未文档化 |
| `vis.confirm` | 新增文档 | 视觉确认 | ⚠️ 未文档化 |
| `vis.skip` | 新增文档 | 视觉跳过 | ⚠️ 未文档化 |
| `vis.batch_confirm` | 新增文档 | 批量视觉确认 | ⚠️ 未文档化 |
| `vis.action` | 新增文档 | 视觉动作 | ⚠️ 未文档化 |
| `interfere_action` | 待实现 | 干预动作 (reexecute/rethink/freeze) | ❌ 未注册 |
| `freeze_request` | 待实现 | 请求冻结 | ❌ 未注册 |
| `unfreeze` | 待实现 | 解除冻结 | ❌ 未注册 |
| `submit_annotation` | 待实现 | 提交冻结标注 | ❌ 未注册 |
| `retry_step` | 待实现 | 重试步骤 | ❌ 未注册 |
| `request_replan` | 待实现 | 请求重新规划 | ❌ 未注册 |
| `confirm_replan` | 待实现 | 确认重新规划 | ❌ 未注册 |

### 后端 → 前端 (Server → Client)

| 消息类型 | 变更 | 说明 | 状态 |
|---------|------|------|------|
| `task.started` | 不变 | 任务启动确认 | ✅ 已验证 |
| `thinking.node_created` | 不变 | 思考节点创建（根节点） | ✅ 已验证 |
| `thinking.node_selected` | 不变 | 思考节点选择（非根节点） | ✅ 已验证 |
| `thinking.option_selected` | 不变 | 选项已选择确认 | ✅ 已验证 |
| `thinking.completed` | 不变 | 思考完成 | ✅ 已验证 |
| `thinking.converged` | 不变 | 思考收敛 | ✅ 已验证 |
| `execution.blueprint_loaded` | 不变 | 执行蓝图加载 | ✅ 已验证 |
| `execution.step_started` | 不变 | 步骤开始 | ✅ 已验证 |
| `execution.step_completed` | 不变 | 步骤完成 | ✅ 已验证 |
| `execution.step_failed` | 不变 | 步骤失败 | ⚠️ 未验证 |
| `execution.intervention_needed` | 不变 | 需要干预 | ⚠️ 未验证 |
| `execution.returned_to_thinking` | 不变 | 返回思考阶段 | ⚠️ 未验证 |
| `execution.completed` | 不变 | 执行完成 | ⚠️ 未验证 |
| `execution.paused` | 不变 | 执行暂停 | ⚠️ 未验证 |
| `execution.resumed` | 不变 | 执行恢复 | ⚠️ 未验证 |
| `execution.replanned` | 不变 | 重新规划 | ⚠️ 未验证 |
| `error` | 不变 | 通用错误 | ⚠️ 未验证 |
| `screenshot` | 待实现 | 截图推送 | ❌ 未实现 |
| `freeze.confirmed` | 待实现 | 冻结确认 | ❌ 未实现 |
| `status_update` | 待实现 | 状态更新 | ❌ 未实现 |
| `replan.result` | 待实现 | 重新规划结果 | ❌ 未实现 |

---

## 版本规划

| 版本 | 目标 | 预计时间 |
|------|------|---------|
| v2.0.0 | 当前已验证的核心链路 | 2025-04-04 |
| v2.1.0 | 补齐干预改造 + 状态更新推送 | Week 1 |
| v2.2.0 | 冻结模式 + 截图推送 | Week 2 |
| v2.3.0 | 视觉系统文档化 + 补齐验证 | Week 3 |
| v3.0.0 | 未来重大重构 | TBD |

---

## 废弃记录

| 废弃项 | 替代方案 | 废弃日期 |
|--------|---------|---------|
| `phase_change` 事件 | `task.started` / `execution.blueprint_loaded` 隐含推断 | 2026-04-23 |
| `thinking_node_added` | `thinking.node_created` | 2026-04-23 |
| `thinking_option_confirmed` | `thinking.option_selected` + `thinking.node_selected` | 2026-04-23 |
| `step_status_changed` | `execution.step_started` / `execution.step_completed` | 2026-04-23 |
| `intervention_required` | `execution.intervention_needed` | 2026-04-23 |
| WS 路径 `/ws/blueprint` | `/ws` | 2026-04-23 |

---

*最后更新: 2026-04-23*
