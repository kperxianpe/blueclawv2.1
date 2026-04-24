# Blueclaw V2.5 Backend

FastAPI + Uvicorn + WebSocket 统一服务

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

服务将启动：
- HTTP REST: `http://localhost:8006/api/ide/*`
- WebSocket: `ws://localhost:8006/ws`
- IDE WebSocket: `ws://localhost:8006/ws/ide`

### 3. 测试连接

```bash
# 运行 E2E 干预链路测试
cd ..
python tests/e2e_intervention_verify_v3.py

# 运行浏览器+标注回传测试
python tests/e2e_freeze_annotation_verify.py

# 或使用 wscat 手动测试
npx wscat -c ws://localhost:8006/ws
```

## 项目结构

```
backend/
├── websocket/
│   ├── __init__.py
│   ├── server.py              # WebSocket 服务
│   ├── message_router.py      # 消息路由（含 5 个干预 handler）
│   └── handlers/
│       ├── adapter_runtime.py # Adapter runtime handlers
│       └── ...
├── core/
│   ├── __init__.py
│   ├── task_manager.py        # 任务管理
│   ├── execution_engine.py    # 执行引擎（含截图钩子）
│   ├── state_sync.py          # 状态同步广播器
│   ├── adapter_runtime_manager.py  # Adapter runtime 状态机
│   └── checkpoint.py          # 状态持久化
├── models/
│   ├── __init__.py
│   ├── task.py                # 任务模型
│   └── messages.py            # 消息类型
├── tests/
│   └── test_websocket.py      # 集成测试
├── checkpoints/               # 检查点存储目录
├── main.py                    # 服务入口
├── requirements.txt           # 依赖
└── README.md                  # 本文档
```

## 接口文档

### 客户端 → 服务端

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `task.start` | 开始新任务 | `{user_input: string}` |
| `select_option` | 选择思考选项（V2 API） | `{nodeId, optionId}` |
| `thinking.select_option` | 选择思考选项 | `{task_id, current_node_id, option_id}` |
| `thinking.confirm_execution` | 确认执行 | `{task_id}` |
| `freeze_request` | 冻结当前步骤+截图 | `{task_id, step_id, reason?}` |
| `submit_annotation` | 提交标注并解冻 | `{task_id, step_id, annotation?, boxes[], freeze_token?}` |
| `retry_step` | 重试失败步骤 | `{task_id, step_id, reason?}` |
| `request_replan` | 请求重新规划 | `{task_id, step_id, context?}` |
| `confirm_replan` | 确认/拒绝重新规划 | `{task_id, step_id, action: 'accept' \| 'reject'}` |

### 服务端 → 客户端

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `task.started` | 任务已创建 | `{task_id, user_input}` |
| `thinking.node_created` | 思考节点生成 | `{node, options, allow_custom}` |
| `thinking.converged` | 思考收敛，自动生成蓝图 | `{final_path, auto_transition}` |
| `execution.blueprint_loaded` | 执行蓝图加载 | `{blueprint: {id, steps[]}}` |
| `execution.step_started` | 步骤开始 | `{step_id, name, status, tool?}` |
| `execution.step_completed` | 步骤完成 | `{step_id, name, status, result, duration_ms}` |
| `freeze.confirmed` | 冻结确认+截图 | `{adapterId, stepId, screenshot, freezeToken}` |
| `screenshot` | 步骤执行截图 | `{adapterId, stepId, image, timestamp}` |
| `annotation.submitted` | 标注已保存 | `{step_id, annotation, boxes[]}` |
| `status_update` | 状态更新 | `{status, step_id, message, ...}` |
| `error` | 错误信息 | `{message}` |

### 冻结 / 标注完整链路

```
Client                                    Server
  | ---------- freeze_request ---------->  |
  |  {task_id, step_id, reason}            |
  |                                        | 1. Find blueprint
  |                                        | 2. Auto-init WebAdapter (if needed)
  |                                        | 3. Screenshot via Playwright
  |                                        | 4. Auto-attach runtime (if needed)
  |                                        | 5. Set runtime state = "frozen"
  | <--------- freeze.confirmed ---------  |
  |  {screenshot: "base64...", freezeToken}|
  |                                        |
  | (User draws boxes on screenshot)       |
  |                                        |
  | ---------- submit_annotation ------->  |
  |  {task_id, step_id, annotation,        |
  |   boxes: [{x,y,w,h,label}]}            |
  |                                        | 6. Save annotation + boxes
  |                                        | 7. Set runtime state = "running"
  |                                        | 8. Resume ExecutionEngine
  | <--------- annotation.submitted -----  |
  |  {step_id, annotation, boxes[{id}]}    |
  | <--------- status_update ------------  |
  |  {status: "resumed", message}          |
```

## 关键设计

### WebAdapter 自动初始化

三个入口点确保截图时浏览器已启动：
1. `ExecutionEngine._maybe_capture_screenshot`
2. `ExecutionEngine._execute_blueprint`
3. `message_router._handle_freeze_request`

### Runtime 自动创建

`freeze_request` 和 `submit_annotation` 在 `adapter_runtime_manager` 中无对应 runtime 时自动 `attach`：

```python
if not adapter_runtime_manager.get(blueprint_id):
    adapter_runtime_manager.attach(blueprint_id, task_id, f"studio_{...}", "web")
```

## 测试

```bash
# 启动服务
python main.py

# 运行 E2E 测试（新窗口）
cd ..
python tests/e2e_freeze_annotation_verify.py
python tests/e2e_intervention_verify_v3.py
python tests/e2e_browser_and_annotation_verify.py
```

## 故障排查

| 问题 | 解决方案 |
|-----|---------|
| Connection refused | 确认服务已启动 (`python main.py`) |
| Module not found | 确认在 backend 目录下运行，或 PYTHONPATH 包含 blueclawv2 根目录 |
| Port already in use | `Get-NetTcpConnection \| ?{$_.LocalPort -eq 8006}` 查看并 kill 进程 |
| Screenshot empty | 检查 Playwright Chromium 是否已安装 (`playwright install chromium`) |
| Google search timeout | 国内网络限制，Skill 系统会自动回退到 LLM 生成结果 |

---

*W2.5 + W3 完成 - 2026-04-24*
