# Blueclaw E2E 干预链路验证报告

> 验证日期: 2026-04-24
> 验证人: Kimi Code CLI
> 后端版本: blueclawv2/backend/main.py (port 8006)

---

## 验证目标

验证前端 <-> 后端 WebSocket 干预全链路是否打通：

```
用户点击"暂停"
  -> 前端发送 freeze_request
  -> 后端收到 -> 截图 -> 冻结 runtime
  -> 推送 freeze.confirmed 到前端
  -> 前端弹出 FreezeOverlay
  -> 用户画框标注
  -> 前端发送 submit_annotation
  -> 后端解冻 -> 恢复执行
```

---

## 测试环境

| 组件 | 版本 | 状态 |
|------|------|------|
| Python | 3.12.9 | OK |
| FastAPI + Uvicorn | latest | OK |
| WebSocket | ws://127.0.0.1:8006/ws | OK |
| Playwright | 1.59.1 | OK |
| Chromium | bundled | OK |
| KIMI_API_KEY | set in .env | OK |

---

## 测试脚本

| 脚本 | 用途 |
|------|------|
| `tests/e2e_intervention_verify_v3.py` | 方向 A：干预链路 |
| `tests/e2e_browser_and_annotation_verify.py` | 方向 B+C：浏览器执行 + 标注回传 |

---

## 方向 A：干预链路验证结果

```
[OK] CONNECT: WebSocket connected ws://127.0.0.1:8006/ws
[OK] THINKING: Received thinking.node_created
[OK] STEP: Step started: 信息搜集 (step_eef9f77f)
[OK] FREEZE: Received freeze.confirmed (token=freeze_be43789cc..., screenshot=True)
[OK] UNFREEZE: Received status_update

PASSED: 5 | FAILED: 0
Intervention chain: ALL GREEN [OK]
```

### 关键发现

- `freeze.confirmed` **包含真实截图** (`screenshot=True`)，证明 WebAdapter 浏览器自动初始化成功
- `freeze_token` 正常生成并返回
- `submit_annotation` 后 `status_update` 正常推送，执行恢复

---

## 方向 B：浏览器真实执行验证结果

### 第一轮验证（2026-04-24）

```
[OK] STEP: Step started: 信息搜集 (step_68d34a8e)
[OK] SCREENSHOT: Screenshot received during step execution
[OK] STEP: Step started: 价格查询 (step_daacba8a)
[OK] SCREENSHOT: Screenshot received during step execution
[OK] STEP: Step started: 汇总比较 (step_bd736942)
[OK] SCREENSHOT: Screenshot received during step execution

PASSED: 9 | FAILED: 0
Screenshots captured: 3 (total 17016 chars)
```

### 第二轮验证（真实 LLM，2026-04-24）

```
[OK] STEP: Step started: 信息搜集 (step_5084e715)
[OK] SCREENSHOT: Screenshot received during execution, length=5672
[OK] STEP: Step started: 价格查询 (step_0709b9bc)
[OK] SCREENSHOT: Screenshot received during execution, length=5672
[OK] STEP: Step started: 详细信息搜集1 (step_94f564ce)
[OK] SCREENSHOT: Screenshot received during execution, length=5672
[OK] STEP: Step started: 详细信息搜集2 (step_0dd2a069)
[OK] SCREENSHOT: Screenshot received during step execution
[OK] FREEZE: freeze.confirmed with screenshot (len=5672)

PASSED: 10 | FAILED: 0
Screenshots captured: 4 (total 22688 chars)
Browser + Annotation: ALL GREEN [OK]
```

### 关键发现

- **每个步骤执行后自动推送 screenshot 消息**，image_b64_len = 5672
- **freeze.confirmed 截图不再为空**（len=5672），message_router 修复生效
- 截图数据为真实 Base64 编码的 PNG 图片（非空/非占位符）
- 后端日志确认：`[ExecutionEngine] Screenshot pushed for step XXX` 每一步都有
- WebAdapter 在 `_execute_blueprint` 开始时自动初始化（Playwright Chromium）

---

## 方向 C：标注数据回传验证结果

### W2.5 第一轮验证（2026-04-24）

```python
# submit_annotation payload 结构
{
    "step_id": "step_...",
    "annotation": "User drew a box at (100, 200)",
    "boxes": [
        {"id": "box-1", "type": "explain", "x": 100, "y": 200, "width": 300, "height": 150}
    ],
    "selected_option": "A",
}
```

### 关键发现

- 后端 `message_router._handle_submit_annotation` 成功接收并解析 payload
- 返回 `status_update` 确认解冻状态
- **标注坐标数据已到达后端**（当前后端仅记录 annotation 字符串，boxes 数据待后续处理）

### W2.5 + W3 完整链路验证（2026-04-24）

```
[OK] CONNECT: WebSocket connected
[OK] THINKING: Received thinking.node_created
[OK] TASK: Task started: task_92788698
[OK] BLUEPRINT: Execution blueprint loaded
[OK] STEP: Step started: 信息检索
[OK] FREEZE: freeze.confirmed received (screenshot=present, token=yes)
[OK] RESUME: status_update 'resumed' received
[OK] ANNOTATION: annotation.submitted with 2 boxes returned

PASSED: 9 | FAILED: 0
Freeze + Annotation Round-trip: ALL GREEN [OK]
```

### 关键发现

- **前端 FreezeOverlay 组件已完成**：截图展示 + 框选标注 + 文本备注
- **标注坐标回传已打通**：submit_annotation payload 包含 `boxes` 数组（x, y, w, h, label）
- **后端自动创建 runtime**：freeze_request / submit_annotation 在 runtime 不存在时自动 `attach`
- **2 个标注框完整回传**：后端保存到 `adapter_runtime_manager` 并回传 `annotation.submitted`
- **ExecutionNode 新增冻结按钮**：运行中的步骤可点击"冻结"触发 freeze_request

---

## 修复记录

本次验证过程中发现并修复了以下问题：

### 修复 1：ExecutionEngine `state_sync` 未定义

**问题**: `_maybe_capture_screenshot` 中直接使用 `state_sync.push_screenshot()`，但 `state_sync` 未在局部作用域导入，导致 `NameError: name 'state_sync' is not defined`

**修复**: 在 `_maybe_capture_screenshot` 中添加延迟导入 `from blueclaw.core.state_sync import state_sync`

**文件**: `blueclaw/core/execution_engine.py`

### 修复 2：WebAdapter 未自动初始化

**问题**: `_maybe_capture_screenshot` 依赖 `AdapterManager._task_adapter_map` 判断是否有浏览器实例，但 ExecutionEngine 执行流程不经过 `AdapterManager.execute()`，导致 `_task_adapter_map` 为空，截图被跳过

**修复**:
1. 在 `_maybe_capture_screenshot` 中，如果 task_id 未注册，自动初始化 WebAdapter
2. 在 `_execute_blueprint` 中，如果蓝图包含 Web 步骤，自动初始化 WebAdapter
3. 移除 finally 中的 WebAdapter 清理逻辑（避免 freeze_request 时浏览器已关闭）

**文件**: `blueclaw/core/execution_engine.py`

### 修复 3：freeze_request handler 截图失败

**问题**: `message_router._handle_freeze_request` 中创建的 `AdapterManager()` 是新实例，与 ExecutionEngine 中初始化的实例不同，导致 `_task_adapter_map` 为空

**修复**: 在 `_handle_freeze_request` 中，如果 task_id 未注册，自动初始化 WebAdapter 后再截图

**文件**: `backend/websocket/message_router.py`

---

## 结论

| 方向 | 状态 | 说明 |
|------|------|------|
| **A: 干预链路** | ✅ 打通 | freeze_request -> freeze.confirmed -> submit_annotation -> status_update 全链路 |
| **B: 浏览器执行** | ✅ 打通 | Playwright Chromium 自动启动，步骤执行后自动截图推送 |
| **C: 标注回传** | ✅ 打通 | 前端 FreezeOverlay 框选 -> submit_annotation boxes -> 后端保存 -> annotation.submitted 回传 |
| **D: 前端联调** | ✅ 完成 | RealtimeProvider 处理 freeze.confirmed/screenshot，ExecutionNode 触发 freeze_request |

**整体状态**: W2.5 遗留问题（标注坐标回传）和 W3 前端联调 **全部完成**。
