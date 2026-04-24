# Blueclaw Adapter 执行适配层 (Week 22)

> 将 Core 引擎的 `ExecutionBlueprint` 路由到外部目标环境（Web 浏览器 / IDE 编辑器）。

## 与 backend/adapter/ 的区别

- `backend/adapter/`：**元工具层**（AI工具的工具），用于构建可复用的单工具/工作流/Agent组合。
- `blueclaw/adapter/`：**执行适配层**（本目录），负责把 Core 生成的蓝图翻译成具体环境可执行的动作。

## 核心组件

| 文件 | 职责 |
|------|------|
| `manager.py` | `AdapterManager`：蓝图路由、生命周期管理、与 Core 层通信 |
| `models.py` | Pydantic 模型：`ExecutionBlueprint`、`ExecutionStep`、`ActionDefinition`、`WebExecutionResult`、`IDEExecutionResult` 等 |
| `state.py` | 状态机 (`idle/planning/executing/validating/paused/completed/failed`) + 事件总线 + 文件持久化 |
| `exceptions.py` | `AdapterException` 基类及 5 个子类（网络/定位/执行/验证/超时）+ JSONL 结构化日志 |
| `adapters/base.py` | `BaseAdapter` 抽象类 |
| `adapters/web.py` | `WebAdapter`（最小实现，预留 Playwright/Selenium 接入点） |
| `adapters/ide.py` | `IDEAdapter`（最小实现，预留 IDE RPC 接入点） |

## 快速使用

```python
from blueclaw.adapter import AdapterManager, ExecutionBlueprint

manager = AdapterManager()

# 从 dict / Pydantic 模型直接执行
blueprint = ExecutionBlueprint(
    task_id="demo-001",
    adapter_type="web",
    steps=[...],
)
result = await manager.execute(blueprint)

# 暂停 / 恢复 / 取消
await manager.pause("demo-001")
await manager.resume("demo-001")
await manager.cancel("demo-001")
```

## 测试

```bash
python -m pytest blueclaw/adapter/tests/unit/test_manager.py -v --cov=blueclaw.adapter --cov-report=term-missing
```

当前覆盖率：~94%（18/18 测试通过）。

## Week 23.5 新增能力（干预闭环）

| 文件 | 职责 |
|------|------|
| `core/operation_record.py` | `OperationRecord` + `OperationLog`：记录每个步骤的执行前/后截图、结果、状态快照 |
| `core/screenshot.py` | `ScreenshotCapture` 抽象 + `PlaywrightScreenshot` + `IDEScreenshot` + WebP 压缩 |
| `core/checkpoint_v2.py` | `CheckpointManagerV2`：基于操作记录保存/恢复检查点，支持保留最近 N 个 |
| `ui/intervention/` | `InterventionUI` 抽象 + `WebInterventionUI`（aiohttp + Canvas 画圈）/ `PopupInterventionUI`（Tkinter）/ `CliInterventionUI`（命令行） |
| `core/replan_engine.py` | `AdapterReplanEngine`：基于检查点和用户干预生成新蓝图，支持 retry/skip/replan |

### 干预闭环执行流程

1. **执行前截图**（可选）
2. **执行步骤**（`_execute_step`）
3. **执行后截图**（强制，WebP 压缩）
4. **创建 `OperationRecord`** 并追加到 `OperationLog`
5. **保存检查点**（`CheckpointManagerV2.save_from_record`）
6. **判断是否需要干预**（失败或步骤要求确认）
7. **展示干预界面**，接收用户选择：
   - `retry`：修改参数后重试当前步骤
   - `skip`：跳过当前步骤，继续后续
   - `replan`：基于检查点 + 干预上下文生成新蓝图，从当前步骤替换后续
   - `abort`：中止任务

### 测试覆盖

- `test_operation_record.py`：序列化、日志查询、上下文构建、JSONL 持久化
- `test_checkpoint_v2.py`：保存、恢复、列表、清理
- `test_replan.py`：replan/skip/retry/merge 蓝图
- `test_intervention_ui.py`：CLI mock、Web 服务启动/提交、HTML 生成

全部 38 项 Adapter 测试通过。

## Week 24 新增能力（Web 模块：真实 Playwright + DOM 分析 + 执行器闭环）

| 文件 | 职责 |
|------|------|
| `web/models.py` | `WebElement`、`PageAnalysis`、`LocationResult`：网页可交互元素与页面分析的数据模型 |
| `web/analyzer.py` | `WebAnalyzer`：通过 Playwright JS 注入提取页面可交互元素，计算 bounding box 与截图归一化坐标 |
| `web/distraction.py` | `DistractionDetector`：DOM 规则 + 轻量截图像素验证，自动标记广告/弹窗/固定栏等干扰元素 |
| `web/locator.py` | `WebLocator`：支持语义文本匹配 → CSS selector → 归一化坐标的三层回退定位策略 |
| `web/executor.py` | `WebExecutor`：执行 navigate/click/input/scroll/select/screenshot/wait 动作，整合截图→分析→过滤→定位→执行→记录→检查点的完整闭环 |
| `adapters/web.py` | `WebAdapter`（升级为真实 Playwright 版）：启动 Chromium，创建 page/context，生命周期管理 |
| `core/screenshot.py` | `PlaywrightScreenshot` 升级为真实 `page.screenshot()` 调用，保留 WebP 压缩能力 |

### Web 执行器动作支持

| 动作 | 说明 |
|------|------|
| `navigate` | `page.goto(url)`，支持 networkidle 等待 |
| `click` | 优先使用元素 CSS selector，fallback 到归一化坐标点击 |
| `input` | `page.fill(selector, text)` |
| `scroll` | `page.evaluate(window.scrollBy)`，无需元素定位 |
| `select` | `page.select_option(selector, value)` |
| `screenshot` | 捕获当前页面截图 |
| `wait` | `page.wait_for_timeout(ms)` |

### 执行闭环流程（单步骤）

1. **执行前截图**
2. **动作路由**：navigate/scroll/wait 无需定位；click/input/select 需要分析与定位
3. **页面分析**（`WebAnalyzer.analyze`）→ 提取可交互元素列表
4. **干扰过滤**（`DistractionDetector.detect`）→ 标记并排除干扰元素
5. **元素定位**（`WebLocator.locate`）→ 语义 / selector / 坐标三层回退
6. **执行 Playwright 动作**，失败时自动重试一次
7. **执行后截图**（WebP 压缩）
8. **生成 `OperationRecord`** 并保存到 `OperationLog`
9. **保存检查点**（`CheckpointManagerV2.save_from_record`）

### 测试覆盖

- `tests/web/test_analyzer.py`：元素提取、归一化坐标、语义字段
- `tests/web/test_distraction.py`：干扰元素检测、正常元素不误判
- `tests/web/test_locator.py`：语义匹配、placeholder 匹配、selector 定位、坐标定位、失败回退
- `tests/web/test_executor_integration.py`：navigate + screenshot、click + fill、scroll + select 的端到端集成

**当前状态**：全部 51 项 Adapter 测试通过（含 Week 22 / Week 23.5 / Week 24）。

## Week 25 新增能力（可靠性机制：检查点 + 验证 + 恢复 + 可视化）

| 文件 | 职责 |
|------|------|
| `web/checkpoint.py` | `WebCheckpointManager`：保存/恢复浏览器页面状态（DOM、Cookies、LocalStorage、SessionStorage、截图），与 `core/checkpoint_v2.py` 的操作记录检查点互补 |
| `web/validator.py` | `WebValidator`：步骤执行后验证（URL 正则匹配、元素存在、文本包含、视觉 SSIM 匹配、自定义函数、超时控制） |
| `web/recovery.py` | `RecoveryController`：自动故障恢复决策树（重试 → 备用选择器 → 回滚 → 暂停干预） |
| `web/visualization.py` | `CanvasMindVisualizer`：通过 `page.evaluate` 向目标页面注入可视化层（红圈脉冲标记、检查点旗帜、干扰元素黄色遮罩、浮动进度条） |
| `ui/intervention/web.py` | 增强干预面板 HTML，支持在 Canvas 上预绘制操作标记 |
| `demo/web_recovery.py` | 表单填写 + fallback selector 自动恢复演示脚本 |

### Web 执行器增强闭环（单步骤）

1. **执行前**：注入可视化覆盖层 + 显示进度条
2. **执行前截图**
3. **执行动作**（navigate / click / input / scroll / select / screenshot / wait）
4. **执行后截图**（WebP 压缩）
5. **验证**（如果 `step.validation` 存在）
6. **自动恢复**（如果失败）：
   - 重试（同参数，最多 N 次，带退避）
   - 备用选择器重试（按 `fallback_selectors` 顺序尝试）
   - 回滚到最近页面状态检查点（`WebCheckpointManager.restore`）
   - 若均失败，返回 `pause` 触发用户干预
7. **可视化标记**：操作位置红圈、干扰元素高亮
8. **保存 WebCheckpoint**（页面状态检查点）
9. **生成 OperationRecord** + 保存 core checkpoint

### 验证类型

| 类型 | 说明 |
|------|------|
| `url_match` | 正则匹配当前页面 URL |
| `presence` | Playwright locator 元素存在性检查（支持 `expected=True` 占位通过） |
| `text_contains` | 元素文本包含验证（支持 `{"selector": "...", "text": "..."}` 或纯字符串） |
| `visual_match` | 截图 SSIM 视觉对比（基于 OpenCV + NumPy，无需 scikit-image） |
| `custom` | 自定义验证函数（支持 sync/async，返回 truthy/falsy） |
| `return_code` | Web 上下文占位（直接返回通过） |

### 恢复策略配置

```python
from blueclaw.adapter.web.recovery import RecoveryConfig

config = RecoveryConfig(
    max_retries=2,
    retry_backoff_ms=500,
    fallback_selectors=["#btn-new", "button[type='submit']"],
    enable_rollback=True,
    pause_on_failure=False,
)
```

### Demo 运行

```bash
python -m blueclaw.adapter.demo.web_recovery
```

输出示例：
```
[Task Start] Register account on test site
Step 1/6: Navigate ... OK
Step 2/6: Wait for page change ... OK
Step 3/6: Fill Username ... OK
Step 4/6: Fill Password ... OK
Step 5/6: Click Submit ... OK (recovered: Recovered via fallback: Fallback selector succeeded: #submit-new)
Step 6/6: Verify Success ... OK
[Task Complete] Registration successful!
```

### 测试覆盖

- `tests/web/test_checkpoint.py`：DOM/Storage/Cookie 保存恢复、清理
- `tests/web/test_validator.py`：URL/presence/text/visual/custom/return_code 验证
- `tests/web/test_recovery.py`：重试成功、备用选择器、回滚、暂停
- `tests/web/test_visualization.py`：覆盖层注入、红圈标记、旗帜、干扰高亮、进度条、清除

**当前状态**：全部 81 项 Adapter 测试通过（Week 22 + Week 23.5 + Week 24 + Week 25）。
