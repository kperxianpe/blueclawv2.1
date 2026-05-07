# Blueclaw v2.5 部署与运行指南

> 文档生成时间: 2026-04-25
> 适用版本: Blueclaw v2.5
> 环境: Windows + Python 3.12 + Node.js + Playwright

---

## 一、项目概述

Blueclaw v2.5 是一个基于 LLM 的智能任务执行系统，核心流程为：

```
用户输入 → 思考蓝图(Thinking Blueprint) → 选项选择 → 执行蓝图(Execution Blueprint) → 逐步执行
```

- **前端**: React 18 + Vite + React Flow，端口 5173
- **后端**: FastAPI + Uvicorn + WebSocket，端口 8006
- **LLM**: Kimi (Moonshot) API，通过 `.env` 配置

---

## 二、环境准备

### 2.1 Python 依赖

```powershell
cd blueclawv2
pip install -r requirements.txt
pip install playwright Pillow
python -m playwright install chromium
```

关键依赖版本:
- playwright 1.58.0+
- Pillow 11.2.1+

### 2.2 前端依赖

```powershell
cd blueclawv2/frontend
npm install
```

### 2.3 API Key 配置

项目根目录的 `.env` 文件已配置 `KIMI_API_KEY`：

```env
KIMI_API_KEY=sk-...
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-8k
```

> 注意: `.env` 和 `.env 1` 内容相同，后端启动时会自动加载 `.env`。

---

## 三、启动方式

### 3.1 手动分步启动

**启动后端:**
```powershell
cd blueclawv2
python start_backend.py
# 或直接进入 backend 目录
python backend/main.py
```

**启动前端:**
```powershell
cd blueclawv2
python start_frontend.py
# 或
npm run dev -- --port 5173 --host 127.0.0.1
```

**验证服务:**
- 后端: http://localhost:8006 (Uvicorn 运行中)
- 前端: http://127.0.0.1:5173
- WebSocket: ws://127.0.0.1:8006/ws

### 3.2 一键运行脚本（推荐）

```powershell
cd blueclawv2
python run_blueclaw.py

# 自定义任务
python run_blueclaw.py "帮我搜索Python教程"
```

**脚本特性:**
- 自动检测端口 8006/5173，服务已运行则复用
- 自动启动后端（`backend/main.py`）
- 自动启动前端（`npm run dev`）
- 使用 Playwright 同步 API 打开 Chromium
- 全流程自动化：输入 → 思考蓝图 → 选项选择 → 执行蓝图 → 截图
- 截图保存到 `screenshots/YYYYMMDD_HHMMSS/`
- Ctrl+C 优雅退出，自动清理子进程

---

## 四、运行效果

### 4.1 正常流程截图

| 截图 | 说明 |
|------|------|
| S0_initial.png | 页面初始状态，左侧思考画布，右侧 vis-adapter |
| S1_input_filled.png | 输入框已填入任务 |
| S2_submitted.png | 点击发送后，等待 LLM 响应 |
| S3_first_thinking_node.png | 首个思考节点出现，显示问题标题和"待选择" |
| S4_expanded.png | 节点展开，显示选项 A/B/C 及详细描述 |
| S5_round1_selected.png | 选择选项 A 后，显示"已选择: xxx" |
| S6_execution_or_next.png | **执行蓝图出现**，右上角"思考中"→"执行中" |
| S7_execution_progress.png | 执行步骤加载完成，检测到 N 个执行步骤 |

### 4.2 成功标志

1. **思考蓝图**: 节点正常生成、展开、选项展示、选择后状态变为"已选择"
2. **执行蓝图**: 右上角状态变为"执行中"，右侧出现执行步骤节点流
3. **WebSocket**: 控制台日志显示 `thinking.node_created` → `task.started` → 执行阶段消息

### 4.3 最终验证截图示例

执行阶段截图显示：
- 思考节点: "已选择: 技术科普"（带 ✨ 标记）
- 执行蓝图: 多个执行步骤节点（信息检索、价格查询、汇总、方案对比等）
- 状态栏: "执行中"

---

## 五、遇到的问题与解决方案

### 5.1 pytest-asyncio Event Loop 冲突

**现象:**
```
RuntimeError: Runner.run() cannot be called from a running event loop
```

**原因:** pytest-playwright 和 pytest-asyncio 的 event loop 机制冲突。

**解决:** 放弃 pytest 框架，改用 **Playwright 同步 API** (`playwright.sync_api`) 编写 standalone 脚本。

### 5.2 前端 Store API 不兼容

**现象:**
```
TypeError: window.__BLUECLAW_STORE__.getState is not a function
```

**原因:** 前端使用 Zustand，暴露的 `__BLUECLAW_STORE__` 可能是函数而非 Redux 风格的对象。

**解决:** `get_store_state()` 函数添加兼容逻辑：
```python
let s = (typeof store === 'function') ? store() : (store.getState ? store.getState() : store);
```

### 5.3 选项按钮选择器匹配到 Disabled 按钮

**现象:** Playwright 点击超时 30s，匹配到 disabled 的"重新思考"按钮。

**原因:** "重新思考"按钮在 disabled 状态下 class 包含 `bg-gray-700`，与选项按钮选择器重叠。

**解决:**
1. 只使用 `bg-gray-800` 选择器（选项按钮用这个 class）
2. 点击前检查 `is_enabled()` 和 `is_visible()`
3. 排除包含"重新思考"/"取消"/"确认"文本的按钮

### 5.4 多轮思考节点未自动处理

**现象:** 只选择了第一个思考节点，后续节点出现后脚本卡死等待执行阶段。

**原因:** 后端可能生成多个思考节点（本例中最多检测到 4 个），每个都需要选择。

**解决:** 添加循环逻辑，自动检测并处理所有 pending 状态的思考节点：
```python
for round_idx in range(10):
    # 查找并点击当前可用选项
    # 等待后端响应（新节点或执行阶段）
    # 如果进入执行阶段则退出
```

### 5.5 变量名残留导致 NameError

**现象:**
```
NameError: name 'execution_reached' is not defined
```

**原因:** 重构代码时删除了 `execution_reached` 变量定义，但 S7 逻辑仍在引用。

**解决:** 改为动态检测：`has_execution = state.get("phase") == "execution" or ...`

---

## 六、已知限制

1. **自动选择策略**: 脚本始终选择每个思考节点的第一个选项，无法模拟用户具体偏好
2. **执行步骤等待**: 执行蓝图出现后只等待 3 秒截图，不等待所有步骤完成执行
3. **前端复用**: 若前端 5173 已被其他项目占用，脚本可能连接错误的服务
4. **LLM 响应时间**: 首次思考节点生成可能需要 10~60 秒，脚本已设置 90s timeout
5. **截图对比**: 当前仅保存截图，未做像素级差异对比（SSIM 逻辑在 `base_test.py` 中，未集成到运行脚本）

---

## 七、文件清单

```
blueclawv2/
├── run_blueclaw.py          # 一键运行脚本（本指南核心）
├── start_backend.py         # 后端启动脚本
├── start_frontend.py        # 前端启动脚本
├── .env                     # API Key 配置
├── screenshots/             # 截图输出目录
│   └── YYYYMMDD_HHMMSS/
│       ├── S0_initial.png
│       ├── S1_input_filled.png
│       ├── ...
│       └── console_logs.txt
└── dev_log/
    ├── test/                # 早期 pytest 测试（已废弃）
    └── deploy/
        └── DEPLOYMENT_GUIDE.md   # 本文件
```

---

## 八、快速开始

```powershell
# 1. 确保依赖已安装
cd blueclawv2
pip install playwright Pillow
python -m playwright install chromium
cd frontend && npm install

# 2. 一键运行
cd blueclawv2
python run_blueclaw.py

# 3. 查看截图
# 截图保存在 screenshots/ 最新时间戳目录下
```
