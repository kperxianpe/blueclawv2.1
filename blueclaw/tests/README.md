# Blueclaw 测试指南（真实状态版）

> 更新日期: 2026-04-24
> 代码状态: adapter 模块完整，ExecutionEngine-Adapter 对接已部分实现
> 环境: Python 3.12, Windows (GBK 控制台需 `chcp 65001`)

---

## ⚠️ 运行任何测试之前（前置验证）

> **血泪教训**: 曾有开发者直接运行测试脚本，结果 **0/9 全部失败**，报错 `No module named 'blueclaw'`、`gbk codec can't encode` 等环境问题。以下验证步骤帮你区分"环境问题"和"真实功能缺陷"，避免在错误的方向上浪费时间。

### Step 0: 控制台编码（Windows 必做）

```powershell
chcp 65001
$env:PYTHONIOENCODING = "utf-8"
```

> 跳过此步的后果：测试输出中的 `✅❌` 等 Unicode 字符会导致 `gbk codec can't encode` 崩溃，测试还没跑完就挂了。

### Step 1: 3 分钟环境自检

```bash
cd blueclawv2
python blueclaw/tests/self_check.py
```

**预期输出**（2026-04-24 实际验证结果）：

```
[环境层]
[OK] blueclaw/__init__.py 存在
[OK] PYTHONPATH 包含项目根目录
[OK] websockets 已安装
[OK] playwright 已安装
[OK] Playwright Chromium 浏览器已下载

[代码层]
[OK] blueclaw/adapter/ 目录存在
[OK] blueclaw.adapter.manager 可 import
[OK] blueclaw.adapter.models 可 import
[OK] blueclaw.adapter.state 可 import
[OK] blueclaw.adapter.adapters.web 可 import
[OK] blueclaw.adapter.adapters.ide 可 import

[对接层]
[OK] ExecutionEngine 已导入 AdapterManager
[OK] ExecutionEngine 含截图钩子
[OK] WebSocket freeze_request handler 已注册
[OK] WebSocket retry_step handler 已注册
[OK] WebSocket request_replan handler 已注册

[测试层]
[OK] adapter/tests/ 目录存在
[OK] adapter core tests 通过 (18/18)

自检结果: 18/18 通过 (100%)
```

**如果自检未通过**：运行 `python blueclaw/tests/fix_env.py` 自动修复。

### Step 2: 分层验证（按你关心的模块跑）

不要一上来就 `--all`。先跑最小集确认环境 OK，再逐步扩大：

```bash
# 第一层：adapter 核心（最快，0.4 秒）
python -m pytest blueclaw/adapter/tests/core/test_manager.py -q
# 预期: 18 passed

# 第二层：web 模块（~40 秒，涉及 Playwright）
python -m pytest blueclaw/adapter/tests/web -q
# 预期: 50 passed

# 第三层：ide 模块（~13 秒）
python -m pytest blueclaw/adapter/tests/ide -q
# 预期: 56 passed

# 第四层：全部 adapter 测试
python -m pytest blueclaw/adapter/tests -q
# 预期: 124+ passed
```

**如果某一层失败**：看失败的是环境相关（ImportError、Browser not found）还是功能相关（assertion failed）。环境相关的去查【故障排查】表，功能相关的才是真 bug。

### Step 3: 旧测试（蓝色之爪 v1 遗留）

```bash
# 这些脚本在 blueclaw/tests/ 下，不是 adapter/tests/ 下
python blueclaw/tests/test_01_intent_analyzer.py
```

**已知问题**：GBK 编码 + 部分断言与当前 LLM 输出不匹配。**不要以这些旧测试的结果判断 adapter 是否正常。** adapter 的真实状态以 `blueclaw/adapter/tests/` 下的 pytest 套件为准。

---

## 快速开始

```bash
cd blueclawv2

# 1. 环境自检（3分钟）
python blueclaw/tests/self_check.py

# 2. 修复环境（如自检未通过）
python blueclaw/tests/fix_env.py

# 3. 运行核心测试
python -m pytest blueclaw/adapter/tests/core -q

# 4. 运行 web 测试
python -m pytest blueclaw/adapter/tests/web -q
```

## 测试分层

| 层级 | 目录 | 目标 | 当前状态 |
|------|------|------|---------|
| **单元测试** | `blueclaw/adapter/tests/core/` | Manager、StateMachine、Models | ✅ 18/18 通过 |
| **单元测试** | `blueclaw/adapter/tests/web/` | WebExecutor、Locator、Validator | ✅ 50/50 通过 |
| **单元测试** | `blueclaw/adapter/tests/ide/` | IDE Analyzer、Applier、Planner | ✅ 56/56 通过 |
| **集成测试** | `blueclaw/adapter/tests/integration/` | Manager-Blueprint-Adapter 链路 | 🔄 待运行验证 |
| **验收测试** | `blueclaw/adapter/tests/acceptance/` | Week 22 验收场景 | 🔄 待运行验证 |
| **E2E 测试** | `blueclaw/adapter/tests/e2e/` | Web/IDE/混合场景 | 🔄 待运行验证 |
| **性能测试** | `blueclaw/adapter/tests/performance/` | 执行耗时、截图耗时 | 🔄 待运行验证 |
| **稳定性测试** | `blueclaw/adapter/tests/stability/` | 并发、长时运行、内存 | 🔄 待运行验证 |
| **E2E (旧)** | `blueclaw/tests/` | IntentAnalyzer、Integration、WebSocket | 🔄 部分通过（GBK 编码问题） |

## 已知限制

1. **Windows GBK 编码**: 部分旧测试脚本（`blueclaw/tests/test_01_intent_analyzer.py`）输出 Unicode 字符（✅❌）时，Windows 默认 GBK 控制台会报错。解决方式：
   ```powershell
   chcp 65001
   $env:PYTHONIOENCODING = "utf-8"
   ```

2. **ExecutionEngine-Adapter 深度对接**: `execution_engine.py` 中已有 `_maybe_capture_screenshot` 钩子和 `AdapterManager` 导入，但 Web 步骤的真实浏览器执行链路尚未在 E2E 中完整验证。

3. **干预功能**: WebSocket handlers 已注册（`freeze_request`、`retry_step`、`request_replan`、`submit_annotation`、`confirm_replan`），业务逻辑已在 `message_router.py` 中实现，但完整 E2E 验证待跑通。

## 参考运行记录

### Adapter 单元测试

```bash
# adapter core tests (已验证)
$ python -m pytest blueclaw/adapter/tests/core/test_manager.py -q
============================= 18 passed in 0.42s ==============================

# adapter web tests (已验证)
$ python -m pytest blueclaw/adapter/tests/web -q
============================= 50 passed in 39.66s =============================

# adapter ide tests (已验证)
$ python -m pytest blueclaw/adapter/tests/ide -q
============================= 56 passed in 13.41s =============================

# adapter 全部测试（已验证 124+ 通过）
$ python -m pytest blueclaw/adapter/tests -q
```

### E2E 干预链路验证（2026-04-24 验证通过）

```bash
# 方向 A：干预链路 freeze_request -> freeze.confirmed -> submit_annotation -> status_update
$ python tests/e2e_intervention_verify_v3.py
PASSED: 5 | FAILED: 0
Intervention chain: ALL GREEN [OK]
# freeze.confirmed 包含真实截图 screenshot=True

# 方向 B：浏览器真实执行 + 截图推送
$ python tests/e2e_browser_and_annotation_verify.py
PASSED: 9 | FAILED: 0
Screenshots captured: 3 (total 17016 chars)
Browser + Annotation: ALL GREEN [OK]
# 每个步骤执行后自动推送 screenshot 消息

# 方向 C：标注数据回传（坐标 + 选项）
# submit_annotation payload 包含 boxes + selected_option
# 后端接收并返回 status_update 确认
```

### Adapter Demo

```bash
$ python blueclaw/adapter/demo/web_recovery.py
# -> 输出自愈流程日志
```

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `No module named 'blueclaw'` | PYTHONPATH 不包含项目根目录 | `set PYTHONPATH=%CD%;%PYTHONPATH%` |
| `playwright._impl._errors.Error: Browser not found` | Chromium 未下载 | `playwright install chromium` |
| 控制台输出乱码 | Windows GBK 编码 | `chcp 65001` |
| `ModuleNotFoundError: No module named 'websockets'` | 依赖未安装 | `pip install websockets` |
