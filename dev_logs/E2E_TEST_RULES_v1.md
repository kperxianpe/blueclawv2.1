# Blueclaw v2.5 E2E 测试流程规则 v1.0

**生效日期**: 2026-04-27  
**适用范围**: Blueclaw v2.5 端到端验证（思考蓝图 → 执行蓝图 → Adapter 执行 → vis-adapter）  
**目标**: 任何测试人员拿到这份文档，可以独立执行一轮完整的 E2E 验证并产出可复现的报告。

---

## 一、已发现的测试流程问题（必须规避）

### 问题 1：测试后不清理环境 → 进程僵尸

**现象**: E2E 跑完后后台残留 4 组+ Chromium headless 实例，每组 1GB+ 虚拟内存。多次测试后内存耗尽。  
**根因**: Playwright `browser.close()` 没有等待所有子进程退出；后端 WebAdapter 的浏览器实例也未回收。  
**规避**: 每次测试后强制执行「环境清理检查清单」（见 §3.6）。

### 问题 2：不确认端口就启动服务 → 冲突/假成功

**现象**: 旧服务还在 8006/5173 上跑，新测试直接启动新实例，导致端口冲突或连接到了旧实例。  
**规避**: 启动前必须用 `ss -tlnp | grep 8006` 确认端口空闲。

### 问题 3：前端启动方式错误 → 404

**现象**: 用 `python3 -m http.server` 服务 dist 目录，React SPA 路由返回 404。  
**规避**: 必须用 `vite preview`（支持 SPA fallback）或 `npm run dev`。

### 问题 4：后端日志缓冲 → "引擎没跑"假阴性

**现象**: 执行蓝图已出现，但日志文件为空，误以为后端挂了。  
**规避**: 必须用 `stdbuf -oL python3 -u backend/main.py` 行缓冲模式启动。

### 问题 5：截图命名随意 → 无法追溯

**现象**: S0, S1, S2... 编号不对应实际步骤，不同测试人员编号规则不同。  
**规避**: 强制使用 `[模块]_[用例ID]_[检查点名称]_[HHMMSS].png` 格式。

### 问题 6：没有明确的通过/失败判定标准

**现象**: "看起来对了"不等于"通过了"。执行蓝图出现了但可能没真实执行。  
**规避**: 每个检查点必须有明确的「预期结果」和「判定条件」，截图只是辅助证据。

### 问题 7：测试之间无隔离 → 状态污染

**现象**: 上一轮测试的 sessions/screenshots/console logs 残留在项目目录中，干扰下一轮判断。  
**规避**: 每次测试前清理历史截图目录（或按时间戳新建子目录）。

---

## 二、测试规则总览

```
┌─────────────────────────────────────────────────────────────┐
│  1. 环境准备（前置检查 + 清理旧环境 + 启动服务）                │
│  2. 按题库执行（逐条用例 → 逐检查点 → 操作 + 截图 + 记录）     │
│  3. 结果分析（截图对比预期 / 后端日志核对 / 进程检查）          │
│  4. 修复登记（发现问题 → 记录根因 → 分配修复人 → 预估时间）      │
│  5. 回归测试（修复完成后，重跑对应用例 + 关联用例）              │
│  6. 环境清理（强制关闭所有残留进程 + 归档截图）                 │
└─────────────────────────────────────────────────────────────┘
```

**核心原则**: 一次测试 = 一个干净的沙盒。不干净的沙盒不开始下一轮。

---

## 三、详细规则

### 3.1 环境准备检查清单（必须逐条确认）

| # | 检查项 | 命令/方法 | 预期结果 |
|---|--------|-----------|---------|
| 1 | 端口 8006 空闲 | `ss -tlnp \| grep 8006` | 无输出 |
| 2 | 端口 5173 空闲 | `ss -tlnp \| grep 5173` | 无输出 |
| 3 | 无残留 Chromium | `ps aux \| grep chrome-headless \| grep -v grep \| wc -l` | 输出 `0` |
| 4 | 无残留 Playwright | `ps aux \| grep "playwright/driver" \| grep -v grep \| wc -l` | 输出 `0` |
| 5 | 工作目录正确 | `pwd` | `/root/.openclaw/workspace/blueclawv2.1` |
| 6 | .env 存在 | `cat .env \| grep KIMI_API_KEY` | 显示已配置 |
| 7 | 截图目录清空/新建 | `mkdir -p screenshots/$(date +%Y%m%d_%H%M%S)` | 成功创建 |

**如果任何一项不满足，先执行 §3.6 环境清理，再重新开始。**

### 3.2 服务启动标准流程

**后端**（必须行缓冲，日志实时可 tail）：
```bash
cd /root/.openclaw/workspace/blueclawv2.1
stdbuf -oL python3 -u backend/main.py > backend/exec_debug.log 2>&1 &
```

**前端**（必须 SPA fallback）：
```bash
cd /root/.openclaw/workspace/blueclawv2.1/frontend
npx vite preview --port 5173 --host 127.0.0.1 > /dev/null 2>&1 &
```

**验证服务就绪**（等待最多 15 秒）：
```bash
curl -s http://127.0.0.1:5173 | head -5   # 应返回 HTML
tail -5 backend/exec_debug.log              # 应显示 "Application startup complete"
```

### 3.3 测试题库（题库驱动执行）

题库按模块组织。每个用例包含：
- **用例ID**: 如 TB-001, EB-003, AD-002
- **场景描述**: 一句话说明测什么
- **前置条件**: 开始此用例前系统必须处于什么状态
- **操作步骤**: 逐条用户操作（点击/输入/等待）
- **检查点列表**: 每个检查点 = 一个截图 + 判定标准
- **预期结果**: 用例通过的全部条件
- **风险项**: 容易出问题的环节，需要重点观察

#### 题库结构

```
Module 1: Thinking Blueprint（思考蓝图）
  TB-001: 基础意图理解 — 输入后思考节点正常展开
  TB-002: 选项交互 — 点击节点展开选项，选项内容可识别
  TB-003: 选择反馈 — 选A后进入下一轮或执行阶段

Module 2: Execution Blueprint（执行蓝图）
  EB-001: 执行蓝图生成 — 思考完成后执行节点出现
  EB-002: 执行状态同步 — 节点颜色/状态随执行推进变化
  EB-003: 执行全部完成 — 所有节点标记为完成，无卡死

Module 3: Adapter Execution（Adapter 执行）
  AD-001: 真实 Bing 搜索 — 后端日志出现 cn.bing.com 请求
  AD-002: WebAdapter 浏览器操作 — WebAdapter 成功 navigate + 截图
  AD-003: 浏览器进程回收 — 任务完成后无残留 Chromium

Module 4: vis-adapter 面板
  VA-001: 占位 UI → 内容切换 — vis-adapter 从"拖拽工具"变为真实内容
  VA-002: 截图/HTML 渲染 — vis-adapter 显示 Bing 搜索结果或操作页面
  VA-003: 多步骤内容更新 — 不同步骤 vis-adapter 内容随之更新

Module 5: System Stability（系统稳定性）
  ST-001: WebSocket 断开后端存活 — 前端关闭后后端仍完成执行
  ST-002: 内存不泄漏 — 多次 E2E 后内存占用不持续增长
  ST-003: 并发任务隔离 — 同时提交两个不同任务，结果不互相污染
```

#### 示例用例（AD-001: 真实 Bing 搜索）

| 字段 | 内容 |
|------|------|
| **用例ID** | AD-001 |
| **所属模块** | Module 3: Adapter Execution |
| **场景描述** | 验证后端 ExecutionEngine 调用的 SearchSkill 是否真实访问 Bing，而非 mock 返回 |
| **前置条件** | TB-003 已通过（已进入执行阶段）；后端日志在行缓冲模式下可实时查看 |
| **操作步骤** | 1. 输入"搜索无人机视频" → 开始<br>2. 思考蓝图选A<br>3. 等待执行蓝图出现<br>4. 持续 tail 后端日志 |
| **检查点列表** | CP1: 日志中出现 `[Execution] Using bound tool: skill-search`<br>CP2: 日志中出现 `cn.bing.com/search?q=...`<br>CP3: 返回结果中包含真实网页标题（非 mock 数据） |
| **预期结果** | 三个检查点全部满足；返回结果包含真实的 Bing 搜索结果条目 |
| **风险项** | 国内网络下 Bing 可能被重定向到 cn.bing.com；SearchSkill 可能 fallback 到 mock |
| **失败处理** | 如果 CP2 不满足 → 检查 SearchSkill 默认引擎是否为 Bing；检查网络连通性 |

### 3.4 截图规则

**命名格式**:
```
[模块简写]_[用例ID]_[检查点名称]_[时间戳].png
```

示例：
- `M1_TB001_initial_153045.png`
- `M3_AD001_bing_request_153210.png`
- `M5_ST001_ws_disconnect_153830.png`

**截图时机**:
- 每个检查点**必须**截图（无论通过还是失败）
- 失败时额外截取全屏 + 当前元素高亮
- 后端日志关键行也截图或复制文本保存

**目录结构**:
```
screenshots/
  └── 20260427_153039/
      ├── M1_TB001/
      │   ├── initial_153045.png
      │   └── options_expanded_153052.png
      ├── M3_AD001/
      │   ├── bing_request_153210.png
      │   └── result_page_153215.png
      └── report.md   # 本轮测试的简要报告
```

### 3.5 结果分析与判定

**三级判定**:

| 级别 | 含义 | 处理方式 |
|------|------|---------|
| **PASS** | 检查点全部满足，截图与预期一致 | 记录通过，继续下一个用例 |
| **FAIL** | 检查点不满足，功能确实有问题 | 记录失败原因 + 截图证据，进入 §3.7 修复登记 |
| **GAP** | 无法判定（如网络问题、LLM 随机性导致结果不一致） | 记录"差距原因"，标注为已知限制，不阻塞发布 |

**判定时必须同时检查三个维度**:
1. **前端视觉**: 页面上看到了什么（截图证据）
2. **后端日志**: 引擎实际做了什么（日志文本证据）
3. **系统状态**: 端口、进程、内存是否正常（`ss`/`ps` 证据）

**禁止仅凭"看起来对了"就判定通过。**

### 3.6 环境清理（强制检查清单，每次测试后执行）

| # | 清理项 | 命令 | 预期结果 |
|---|--------|------|---------|
| 1 | 关闭后端 | `kill $(lsof -t -i:8006)` 或找到 PID kill | 端口 8006 释放 |
| 2 | 关闭前端 | `kill $(lsof -t -i:5173)` | 端口 5173 释放 |
| 3 | 清理 Chromium 残留 | `ps aux \| grep chrome-headless \| awk '{print $2}' \| xargs kill -9 2>/dev/null` | 无 chrome-headless 进程 |
| 4 | 清理 Playwright driver | `ps aux \| grep "playwright/driver" \| awk '{print $2}' \| xargs kill -9 2>/dev/null` | 无 playwright driver 进程 |
| 5 | 归档截图 | `mv screenshots/YYYYmmdd_HHMMSS screenshots/archive/` | 截图移动到归档目录 |
| 6 | 清理后端日志 | `> backend/exec_debug.log` 或 `rm backend/exec_debug.log` | 日志文件清空/删除 |
| 7 | 检查 /tmp 残留 | `ls /tmp/playwright_chromiumdev_profile-* 2>/dev/null` | 无残留 user-data-dir |

**注意**: `kill -9` 是强制信号。如果担心误杀，先 `ps aux | grep chromium` 确认 PIDs 再执行。

### 3.7 修复登记与回归测试

**发现问题后必须记录**:

```markdown
## 问题登记
- **用例ID**: AD-001
- **检查点**: CP2（Bing 请求）
- **现象**: 日志中未出现 cn.bing.com，SearchSkill 返回了 mock 数据
- **根因**: SearchSkill 中 engine 参数未正确传递到 WebAdapter
- **修复文件**: `blueclaw/skills/search_skill.py`
- **修复人**: @AI
- **修复时间**: 2026-04-27 16:00
- **回归用例**: AD-001, AD-002, EB-003（搜索功能相关的上游用例）
```

**回归测试规则**:
1. 修复完成后，**必须**重跑失败的用例
2. 如果修复涉及公共模块（如 ExecutionEngine、WebAdapter），**必须**重跑该模块全部用例
3. 回归测试前，**必须**重新执行 §3.6 环境清理
4. 回归测试通过后，在问题登记中标注 `回归验证: ✅ PASS @ 时间戳`

---

## 四、执行模式：人工 vs 智能体

### 4.1 核心问题：谁来检查截图？

用户的问题是："每执行一步就截图，每截图一次就分析是否符合预期，这个分析需要智能体（AI）来做吗？"

**答案是：理想情况下，检查应该是自动化的（脚本层断言），而不是每次都要人眼去看或等 AI 来判断。**

三种模式对比：

| 模式 | 谁执行操作 | 谁截图 | 谁分析 | 效率 | 准确性 |
|------|-----------|--------|--------|------|--------|
| **纯人工** | 人 | 脚本/人 | 人眼对比 | 低 | 中（易疲劳、遗漏） |
| **人操作 + AI分析** | 人 | 脚本 | AI看图+读日志 | 中 | 高（但受限于通信延迟） |
| **全自动化（推荐）** | 脚本 | 脚本 | **脚本断言** | **高** | **高（可重复、无遗漏）** |

### 4.2 推荐模式：脚本内置断言（Assertion Layer）

测试脚本不应该只"走流程截图"，而应该在每个检查点自动判断是否符合预期。

**断言分层**：

```
L1 前端断言: Playwright selector + text matching
  → page.locator("[data-nodeid]").count() > 0
  → page.locator("text='COMPLETED'").is_visible()

L2 后端断言: 日志实时解析
  → tail -f backend/exec_debug.log | grep "Bing request" within 30s
  → grep "StepStatus.COMPLETED" | wc -l == 7

L3 系统断言: 进程/端口/内存检查
  → ss -tlnp | grep 8006 (端口存活)
  → ps aux | grep chrome | wc -l == 0 (无残留)
```

**输出示例**：

```
[TEST] TB-001 开始
[ASSERT] CP1: 页面加载 → L1: selector [data-slot="input"] count=1 ✅
                → L3: port 5173 listening ✅
[PASS] CP1 通过

[ASSERT] CP2: 输入"搜索无人机视频" → L1: input value matches ✅
[PASS] CP2 通过

[ASSERT] CP3: 思考节点出现 → L1: [data-nodeid^='thinking'] count=1 ✅
                → L2: WebSocket message type='thinking_blueprint' received ✅
                → 截图: M1_TB001_thinking_153059.png
[PASS] CP3 通过

[RESULT] TB-001: PASS (3/3)
```

**只有断言失败时，才需要人（或AI）介入分析原因。**

### 4.3 智能体（AI）的角色

AI 不是替代脚本断言，而是处理 **"脚本断言失败后的根因分析"**。

```
正常流程: 脚本自动跑 → 全部断言通过 → 自动生成报告
异常流程: 脚本断言失败 → 截图+日志打包 → AI分析根因 → 输出修复建议
```

AI 擅长：
- 看截图理解页面异常状态
- 读后端日志定位错误栈
- 对比"预期"和"实际"给出修复方向
- 生成修复代码

AI 不擅长（也不该做）：
- 逐张截图肉眼对比（太慢、token 浪费）
- 重复性机械操作（脚本更可靠）

### 4.4 测试执行脚本规范

如果编写自动化测试脚本，必须遵守以下规范：

#### 4.4.1 脚本结构

```python
import atexit          # 注册退出清理
import signal          # 捕获 Ctrl+C

def cleanup():
    """强制清理所有残留进程"""
    # ... kill chromium, playwright, backend, frontend

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: cleanup())

class Checkpoint:
    def __init__(self, name, l1_assert=None, l2_assert=None, l3_assert=None):
        self.name = name
        self.l1 = l1_assert  # 前端断言函数
        self.l2 = l2_assert  # 后端断言函数
        self.l3 = l3_assert  # 系统断言函数
    
    async def verify(self, page, log_file):
        results = []
        if self.l1:
            results.append(("L1", await self.l1(page)))
        if self.l2:
            results.append(("L2", await self.l2(log_file)))
        if self.l3:
            results.append(("L3", await self.l3()))
        return results
```

#### 4.4.2 脚本输出格式

测试脚本 stdout 必须按统一格式输出，方便后续解析：

```
[TEST] 开始用例 TB-001
[STEP] 1. 打开页面 http://127.0.0.1:5173
[CHECK] CP1: 初始界面 → [PASS] 截图: M1_TB001_initial_153045.png
[STEP] 2. 输入任务
[CHECK] CP2: 输入框可用 → [PASS]
[STEP] 3. 点击开始按钮
[CHECK] CP3: 思考节点出现 → [PASS] 截图: M1_TB001_thinking_153059.png
[RESULT] TB-001: PASS (3/3 检查点通过)
---
[TEST] 开始用例 AD-001
...
[RESULT] AD-001: FAIL @ CP2 — 日志中无 Bing 请求
```

#### 4.4.3 截图与日志关联

每个截图文件名必须与检查点名称对应，方便人工复核时"看图就知道测的是什么"。

#### 4.4.4 断言失败时的上下文打包

当断言失败时，脚本应自动收集以下信息并输出为 JSON，方便 AI 分析：

```json
{
  "case_id": "AD-001",
  "checkpoint": "CP2",
  "assertion_level": "L2",
  "assertion_detail": "日志中应出现 'cn.bing.com/search?q=' 但 30s 内未匹配到",
  "screenshot_paths": ["M3_AD001_bing_request_153210.png"],
  "log_snippet": "[EXEC] Starting step: 查询流媒体平台价格\n[Execution] Using bound tool: skill-search\n[MCP] Using mock tools",
  "system_state": {
    "port_8006": true,
    "port_5173": true,
    "chromium_count": 0,
    "memory_mb": 2456
  }
}
```

**AI 收到这个 JSON 后，可以直接定位问题："MCP Using mock tools → SearchSkill fallback 到了 mock，没有真实调用 Bing"。**

---

## 五、人员分工建议

| 角色 | 职责 |
|------|------|
| **测试执行人** | 按题库逐条执行 → 操作 → 截图 → 记录结果 |
| **结果分析人** | 审查截图 + 核对后端日志 → 判定 PASS/FAIL/GAP |
| **修复开发人** | 根据问题登记修复代码 → 自测后提交 |
| **回归验证人** | 修复后重跑用例 → 确认通过 → 关闭问题 |

**单人模式下**（当前状态）：一个人可以兼任所有角色，但必须严格按照「执行 → 记录 → 修复 → 回归」的顺序，不能跳过记录环节。

---

## 六、文档维护

- 每次测试迭代后，将实际遇到的问题和规避方法追加到「§1 已发现的测试流程问题」
- 题库根据产品迭代持续扩展（新增模块/用例/检查点）
- 本规则版本号遵循 `v{major}.{minor}`，重大流程变更升 major，新增用例升 minor

**当前版本**: v1.0  
**下次迭代方向**: 
- 补充 Module 6: Performance（性能基准测试）
- 补充 Module 7: Security（敏感操作检查点）
- 将环境清理脚本封装为 `scripts/test_cleanup.sh`
