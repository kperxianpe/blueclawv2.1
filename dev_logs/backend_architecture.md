# 后端架构文档

> 文档版本: 2025-04-04  
> 对应项目: `blueclawv2/backend/`, `blueclawv2/blueclaw/core/`

---

## 一、技术栈

| 技术 | 版本/说明 | 用途 |
|------|----------|------|
| Python | 3.12.9 | 运行环境 |
| FastAPI | latest | Web 框架 |
| Uvicorn | latest | ASGI 服务器 |
| WebSocket | RFC 6455 | 实时双向通信 |
| SQLite | 内置 | 数据持久化 |
| KIMI API | Moonshot AI | LLM 推理服务 |

---

## 二、功能模块

### 2.1 WebSocket 连接管理器

**位置**: `backend/websocket/` 相关模块

**功能清单**:
- 维护 `connections: Dict[WebSocket, Dict]` 字典
- 每个连接记录: `{task_id, client_info, connected_at}`
- 支持多客户端连接同一任务（广播推送）
- 连接断开时自动清理元数据
- 提供 `get_task_id_for_connection(websocket)` 接口

**连接生命周期**:
```
客户端 connect ──▶ 服务端 accept ──▶ 记录到 connections 字典
                                          │
    ◀─────────── 双向通信阶段 ◀───────────┤
                                          │
客户端 disconnect ──▶ 服务端 on_disconnect ──▶ 从 connections 移除
```

---

### 2.2 消息路由 (Message Router)

**文件**: `backend/websocket/message_router.py`

**功能清单**:
- 消息分发：根据 `message.type` 路由到对应 handler
- Task ID 自动推断：从 WebSocket 连接元数据提取
- V2 协议适配：前端发送的简化消息转换为内部格式
- 未知消息类型返回 error 响应

**Handler 注册表**:
```python
self.handlers = {
    'user_input':    self._handle_task_start,           # 启动任务
    'select_option': self._handle_thinking_select_option, # 选择选项
    'custom_input':  self._handle_thinking_custom_input,  # 自定义输入
}
```

**核心方法 — Task ID 自动推断**:
```python
def _get_task_id(self, websocket, server) -> Optional[str]:
    """从 WebSocket 连接元数据推断 task_id"""
    # 方式1: server 提供专用方法
    if hasattr(server, 'get_task_id_for_connection'):
        return server.get_task_id_for_connection(websocket)
    
    # 方式2: 从 connections 字典读取
    if hasattr(server, 'connections') and websocket in server.connections:
        conn_info = server.connections[websocket]
        if isinstance(conn_info, dict):
            return conn_info.get("task_id") or None
    
    return None
```

**核心方法 — 消息路由入口**:
```python
async def route(self, websocket, message: dict, server) -> dict:
    msg_type = message.get("type", "unknown")
    payload = message.get("payload", {})
    
    # 自动注入 task_id（如果前端未提供）
    if isinstance(payload, dict):
        task_id = payload.get("task_id", "")
        if not task_id:
            conn_task_id = self._get_task_id(websocket, server)
            if conn_task_id:
                payload = {**payload, "task_id": conn_task_id}
    
    # 路由到对应 handler
    handler = self.handlers.get(msg_type)
    if handler:
        return await handler(websocket, payload, server)
    
    return {"type": "error", "error": f"Unknown message type: {msg_type}"}
```

**为什么需要 Task ID 自动推断**: 前端 V2 协议中 `task_id` 为空字符串，后端必须根据连接上下文推断，否则无法定位任务状态。

---

### 2.3 Thinking Engine (思考引擎)

**文件**: `blueclaw/core/thinking_engine.py`

**功能清单**:
- 管理思考节点树（按 task_id 索引）
- 生成思考节点（调用 LLM API）
- 处理选项选择
- 判断思考收敛条件
- 自动选择高置信度选项
- 生成执行蓝图

**核心配置参数**:
```python
class ThinkingEngine:
    MAX_DEPTH = 3                    # 最大思考深度（层数）
    AUTO_SELECT_THRESHOLD = 0.85     # 自动选择置信度阈值
```

#### 2.3.1 思考节点生成流程

```
用户输入 ──▶ 生成根节点 (depth=0)
                │
                ▼
         显示选项 A/B/C
                │
                ▼
         用户选择选项
                │
                ▼
         生成子节点 (depth=1)
                │
                ▼
         显示新选项
                │
                ▼
         用户选择选项
                │
                ▼
         生成子节点 (depth=2)
                │
                ▼
         depth >= MAX_DEPTH ──▶ 思考收敛 ──▶ 生成蓝图
```

#### 2.3.2 选项选择核心逻辑

```python
async def select_option_impl(self, task_id, node_id, option_id, custom_input=None):
    # 1. 获取当前节点
    current_node = self.nodes.get(node_id)
    if not current_node:
        return None
    
    # 2. 标记节点为已解决
    current_node.selected_option_id = option_id
    current_node.status = NodeStatus.RESOLVED
    
    # 3. 确定选中的选项
    selected_option = next(
        (opt for opt in current_node.options if opt.id == option_id), 
        None
    )
    if custom_input:
        selected_option = ThinkingOption(
            id="custom", 
            label="自定义", 
            description=custom_input, 
            confidence=1.0, 
            recommended=True
        )
    
    if not selected_option:
        return None
    
    # 4. 检查是否达到最大深度
    current_path = self._get_thinking_path(task_id, node_id)
    if len(current_path) >= self.MAX_DEPTH:
        return None  # 触发收敛
    
    # 5. 生成下一个思考节点
    next_node_index = len(self.task_nodes.get(task_id, []))
    next_node = await self._generate_next_node(
        task_id, 
        node_id, 
        context=selected_option.description,
        index=next_node_index
    )
    
    # 6. 检查是否触发自动选择
    if next_node:
        auto_option_id = self.should_auto_select(next_node)
        if auto_option_id:
            # 递归自动选择
            return await self.select_option_impl(
                task_id, 
                next_node.id, 
                auto_option_id
            )
    
    return next_node
```

#### 2.3.3 自动选择逻辑

```python
def should_auto_select(self, node: ThinkingNode) -> Optional[str]:
    """
    当某个选项的置信度 >= AUTO_SELECT_THRESHOLD 时，自动选择该选项。
    返回 option_id 或 None。
    """
    for option in node.options:
        if option.confidence >= self.AUTO_SELECT_THRESHOLD:
            return option.id
    return None
```

**自动选择触发场景**:
- LLM 对某个选项非常有信心（confidence >= 0.85）
- 用户无需看到该节点，系统自动推进
- 减少不必要的用户交互

---

### 2.4 State Sync (状态同步管理器)

**文件**: `blueclaw/core/state_sync.py`

**功能清单**:
- 将后端状态变更广播给所有连接的客户端
- 按 task_id 过滤推送目标
- 提供标准化消息封装

**广播方法列表**:

| 方法 | 发送消息类型 | 触发时机 |
|------|------------|---------|
| `push_thinking_node_created(task_id, node)` | `thinking.node_created` | 根节点生成 |
| `push_thinking_node_selected(task_id, node)` | `thinking.node_selected` | 非根节点生成 |
| `push_thinking_option_selected(task_id, node_id, option_id)` | `thinking.option_selected` | 用户选择选项后 |
| `push_thinking_completed(task_id)` | `thinking.completed` | 思考链完成 |
| `push_thinking_converged(task_id)` | `thinking.converged` | 思考收敛 |
| `push_execution_blueprint_loaded(task_id, blueprint)` | `execution.blueprint_loaded` | 蓝图生成完毕 |
| `push_execution_step_started(task_id, step_id)` | `execution.step_started` | 步骤开始执行 |
| `push_execution_step_completed(task_id, step_id, result)` | `execution.step_completed` | 步骤执行成功 |
| `push_execution_step_failed(task_id, step_id, error)` | `execution.step_failed` | 步骤执行失败 |
| `push_execution_intervention_needed(task_id, step_id)` | `execution.intervention_needed` | 需要人工干预 |
| `push_execution_returned_to_thinking(task_id)` | `execution.returned_to_thinking` | 执行回退到思考 |

**消息封装格式**:
```python
{
    "type": "thinking.node_created",
    "payload": { ... },
    "message_id": str(uuid.uuid4()),
    "timestamp": datetime.utcnow().isoformat()
}
```

---

### 2.5 执行引擎

**功能清单**:
- 接收思考收敛后的蓝图（步骤列表 + 依赖关系）
- 拓扑排序确定执行顺序
- 按顺序执行步骤（支持并行执行无依赖步骤）
- 每个步骤可调用外部工具/API
- 步骤失败时：触发干预 / 重试 / 回退到思考
- 步骤完成后更新状态并广播

**执行流程**:
```
蓝图加载 ──▶ 拓扑排序 ──▶ 步骤1执行 ──▶ 步骤2执行 ──▶ ...
                │            │              │
                │            ▼              ▼
                │      [成功/失败]      [成功/失败]
                │            │              │
                │            ▼              ▼
                │      广播completed   广播failed/intervention
                │            │              │
                └────────────┴──────────────┘
                             ▼
                       所有步骤完成 ──▶ phase = completed
```

---

## 三、后端入口文件

| 文件 | 用途 | 启动命令 |
|------|------|---------|
| `backend/main.py` | 开发模式主入口 | `python backend/main.py` |
| `backend/unified_server.py` | 统一服务器入口（生产） | `python backend/unified_server.py` |

---

## 四、调参接口

**文件**: `blueclaw/core/thinking_engine.py`（参数部分）

### 4.1 可调参数列表

| 参数名 | 当前值 | 说明 | 影响 |
|--------|--------|------|------|
| `MAX_DEPTH` | 3 | 最大思考深度 | 思考链长度。值越大，思考越深入，用户交互越多 |
| `AUTO_SELECT_THRESHOLD` | 0.85 | 自动选择置信度阈值 | 越高越不容易自动选择，用户看到更多节点；越低自动选择越多，流程更快 |

### 4.2 调参接口设计

在实际部署中，可通过以下方式动态调整参数：

#### 方式1: 环境变量（推荐用于生产）
```bash
# .env 文件
BLUECLAW_MAX_DEPTH=5
BLUECLAW_AUTO_SELECT_THRESHOLD=0.90
```

```python
# thinking_engine.py
import os

class ThinkingEngine:
    MAX_DEPTH = int(os.getenv('BLUECLAW_MAX_DEPTH', 3))
    AUTO_SELECT_THRESHOLD = float(os.getenv('BLUECLAW_AUTO_SELECT_THRESHOLD', 0.85))
```

#### 方式2: 配置文件
```python
# config.py
from pydantic import BaseSettings

class ThinkingConfig(BaseSettings):
    max_depth: int = 3
    auto_select_threshold: float = 0.85
    
    class Config:
        env_prefix = "BLUECLAW_"

config = ThinkingConfig()
```

#### 方式3: 运行时 HTTP API 调参（动态生效）

```python
# backend/api/admin.py
from fastapi import APIRouter
from blueclaw.core.thinking_engine import ThinkingEngine

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/config")
async def get_config():
    """获取当前思考引擎配置"""
    return {
        "max_depth": ThinkingEngine.MAX_DEPTH,
        "auto_select_threshold": ThinkingEngine.AUTO_SELECT_THRESHOLD,
    }

@router.post("/config")
async def update_config(max_depth: int = None, auto_select_threshold: float = None):
    """
    动态更新思考引擎配置。
    
    参数:
        max_depth: 新的最大思考深度（>= 1）
        auto_select_threshold: 新的自动选择阈值（0.0 ~ 1.0）
    
    返回:
        更新后的配置
    
    注意:
        此修改仅影响新启动的任务，已进行中的任务不受影响。
    """
    if max_depth is not None:
        if max_depth < 1:
            raise HTTPException(status_code=400, detail="max_depth must be >= 1")
        ThinkingEngine.MAX_DEPTH = max_depth
    
    if auto_select_threshold is not None:
        if not 0.0 <= auto_select_threshold <= 1.0:
            raise HTTPException(status_code=400, detail="threshold must be in [0, 1]")
        ThinkingEngine.AUTO_SELECT_THRESHOLD = auto_select_threshold
    
    return {
        "max_depth": ThinkingEngine.MAX_DEPTH,
        "auto_select_threshold": ThinkingEngine.AUTO_SELECT_THRESHOLD,
        "message": "Config updated. New tasks will use these values."
    }
```

**使用示例**:
```bash
# 查看当前配置
curl http://127.0.0.1:8006/admin/config

# 调大思考深度（更深入的规划）
curl -X POST "http://127.0.0.1:8006/admin/config?max_depth=5"

# 调高自动选择阈值（减少自动选择，让用户看到更多选项）
curl -X POST "http://127.0.0.1:8006/admin/config?auto_select_threshold=0.95"

# 同时调整两个参数
curl -X POST "http://127.0.0.1:8006/admin/config?max_depth=4&auto_select_threshold=0.80"
```

### 4.3 调参效果对照表

| 场景 | MAX_DEPTH | AUTO_SELECT_THRESHOLD | 效果 |
|------|-----------|----------------------|------|
| 快速任务（简单查询） | 2 | 0.70 | 思考链短，自动选择多，最快完成 |
| 标准任务（默认） | 3 | 0.85 | 平衡深度和速度 |
| 复杂规划（深度分析） | 5 | 0.90 | 思考链长，用户参与多，结果更精细 |
| 全自动模式 | 3 | 0.60 | 几乎不展示节点，全自动完成 |
| 教学/演示模式 | 5 | 1.00 | 永不自动选择，展示完整思考过程 |

### 4.4 参数生效机制说明

```
用户调参 ──▶ POST /admin/config ──▶ 修改 ThinkingEngine 类属性
                                         │
                                         ▼
                                新任务启动时读取最新值
                                         │
                                ┌────────┴────────┐
                                ▼                 ▼
                          进行中的任务          新任务
                          (使用旧值)            (使用新值)
```

**关键说明**:
- 修改即时生效（无需重启服务）
- 仅影响新启动的任务
- 进行中的任务保持原有参数（保证一致性）
- 建议在任务空闲时调参

---

## 五、关键设计决策

### 5.1 Task ID 自动推断
- **原因**: 前端 V2 协议不管理 task_id，发送空字符串
- **方案**: 后端从 WebSocket 连接元数据自动推断
- **效果**: 前端简化，后端兼容，无需额外认证

### 5.2 思考深度限制 (MAX_DEPTH)
- **原因**: 防止无限思考循环，控制 LLM 调用成本
- **方案**: 硬编码上限，到达后强制收敛
- **效果**: 可预测的执行时间，可控的 API 成本

### 5.3 自动选择机制
- **原因**: 减少用户不必要的点击，加速流程
- **方案**: 置信度阈值触发递归自动选择
- **效果**: 高置信度选项自动通过，低置信度留给用户决策

---

## 六、文件目录

```
blueclawv2/
├── backend/
│   ├── websocket/
│   │   └── message_router.py      # 消息路由 + V2 适配 + Task ID 推断
│   ├── api/
│   │   └── admin.py               # 调参接口 (可选)
│   ├── main.py                     # 开发入口
│   └── unified_server.py           # 统一服务器入口
│
├── blueclaw/
│   ├── core/
│   │   ├── thinking_engine.py      # 思考引擎（核心算法）
│   │   └── state_sync.py           # 状态同步（WS 广播）
│   └── ...
│
├── .env                            # 环境变量 (KIMI_API_KEY)
└── dev_logs/
    └── backend_architecture.md     # 本文档
```

---

## 七、调试指南

### 7.1 后端日志
后端消息路由和 thinking engine 会输出调试日志：
```
[MessageRouter] Routing message: select_option
[MessageRouter] Inferred task_id: task_xxx
[ThinkingEngine] Selecting option A for node thinking_879ebf59
[ThinkingEngine] Generated next node: thinking_7e7d11ae (depth=1)
[StateSync] Broadcasting: thinking.node_selected
```

### 7.2 WebSocket 连接检查
```python
# 在 handler 中检查连接信息
async def _handle_debug(websocket, payload, server):
    task_id = server.get_task_id_for_connection(websocket)
    connections = list(server.connections.keys())
    return {
        "type": "debug.info",
        "payload": {
            "your_task_id": task_id,
            "total_connections": len(connections)
        }
    }
```
