# Blueclaw v2.5 完整部署方案

> 生成时间: 2026-04-29 20:45  
> 版本: v2.5  
> 适用平台: Linux (Ubuntu/Debian/CentOS)

---

## 一、部署架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户浏览器                            │
│                   http://localhost:5173                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    前端 (Vite Preview)                        │
│  • React + Vite 构建产物 (dist/)                            │
│  • 静态文件服务 (npx vite preview)                          │
│  • 端口: 5173                                               │
└─────────────────────────────────────────────────────────────┘
                              │ WebSocket ws://localhost:8006/ws
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    后端 (FastAPI + Uvicorn)                  │
│  • HTTP API: /api/health, /docs                             │
│  • WebSocket: /ws (任务生命周期 + 适配器控制)              │
│  • 端口: 8006                                               │
│  • 依赖: Xvfb (虚拟显示器，供 Playwright 使用)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM API (Moonshot/Kimi)                  │
│  • https://api.moonshot.cn/v1/chat/completions              │
│  • 支持用户在前端填入 API Key，或后端 .env 配置            │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、P0 交付物（已完成 ✅）

### 2.1 补全 requirements.txt

**文件**: `requirements.txt`

```text
# === Core ===
anyio>=3.7.0
asyncio>=3.4.3
httpx>=0.23.0
websockets>=12.0
python-dotenv>=1.0.0

# === Web Framework ===
fastapi>=0.100.0
uvicorn[standard]>=0.23.0

# === LLM Integration ===
openai>=1.0.0

# === Browser Automation ===
playwright>=1.40.0

# === Image Processing ===
Pillow>=10.0.0

# === Code Analysis ===
tree-sitter>=0.25.2

# === Data Models ===
pydantic>=2.0.0
```

**验证:**
```bash
cd /path/to/blueclawv2.1
pip install -r requirements.txt
playwright install chromium  # 安装浏览器依赖
```

### 2.2 前端重新构建

**验证:**
```bash
cd frontend
npm run build
# dist/ 目录生成新文件
```

**构建产物:**
```
dist/index.html          (0.41 kB)
dist/assets/index-*.css  (121.25 kB)
dist/assets/index-*.js   (533.72 kB)
```

### 2.3 .env 清理 + 模板

**文件**: `.env` (已移除明文 key)

```env
KIMI_API_KEY=your_kimi_api_key_here
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-8k
```

**文件**: `.env.example` (模板)

```env
KIMI_API_KEY=sk-your-kimi-api-key-here
KIMI_BASE_URL=https://api.moonshot.cn/v1
```

---

## 三、P1 交付物（已完成 ✅）

### 3.1 健康检查端点

**端点**: `GET /api/health`

**响应:**
```json
{"status": "ok", "version": "2.5"}
```

**验证:**
```bash
curl http://127.0.0.1:8006/api/health
# → {"status":"ok","version":"2.5"}
```

### 3.2 生产启动脚本

**文件**: `start_production.sh`

**功能:**
- 自动检测项目目录（脚本所在目录）
- 自动创建 `logs/` 目录
- 自动检测 `.env` 并提示配置
- 自动检查 `KIMI_API_KEY`
- PID 文件管理（`logs/*.pid`）
- 健康检查自动执行
- `start|stop|restart|status` 四命令

**用法:**
```bash
./start_production.sh start    # 启动
./start_production.sh stop     # 停止
./start_production.sh restart  # 重启
./start_production.sh status   # 查看状态
```

### 3.3 日志持久化

**日志目录**: `logs/`

| 日志文件 | 内容 |
|---------|------|
| `backend.log` | 后端输出 |
| `frontend.log` | 前端预览服务输出 |
| `xvfb.log` | 虚拟显示器输出 |

### 3.4 配置验证启动检查

启动脚本自动检查:
1. `.env` 文件存在性
2. `KIMI_API_KEY` 是否已设置（非默认值）
3. 未设置时输出 WARNING 但不阻止启动

---

## 四、前端 KIMI API Key 输入功能

### 4.1 功能说明

用户可以在前端直接填入 Kimi API Key，该 key 会:
1. 保存到浏览器 `localStorage`（方便下次使用）
2. 提交任务时通过 WebSocket 传给后端
3. 后端保存到 `Config.KIMI_API_KEY`
4. 后续所有 LLM 调用使用该 key

### 4.2 UI 位置

首页输入框上方:
```
🔑 [填入 Kimi API Key（可选，留空则使用系统默认）] [👁]
[帮我规划一个周末旅行...] [开始]
```

### 4.3 截图验证

![部署验证-首页](screenshots/verify/v_deploy_01_home.png)

**可见元素:**
- ✅ API Key 输入框（带 Key 图标）
- ✅ 眼睛图标（显示/隐藏密码）
- ✅ 任务输入框
- ✅ "开始"按钮
- ✅ 快速示例

---

## 五、部署步骤（一键式）

### 5.1 首次部署

```bash
# 1. 克隆/复制项目到目标机器
git clone <your-repo> blueclawv2.1
cd blueclawv2.1

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器
playwright install chromium

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 KIMI_API_KEY

# 5. 构建前端
cd frontend && npm install && npm run build && cd ..

# 6. 启动服务
chmod +x start_production.sh
./start_production.sh start

# 7. 验证
curl http://127.0.0.1:8006/api/health
```

### 5.2 日常运维

```bash
# 查看状态
./start_production.sh status

# 查看日志
tail -f logs/backend.log
tail -f logs/frontend.log

# 重启
./start_production.sh restart
```

---

## 六、验证清单

| # | 验证项 | 方法 | 状态 |
|---|--------|------|------|
| 1 | 前端首页加载 | 打开 http://127.0.0.1:5173 | ✅ |
| 2 | API Key 输入框显示 | 截图确认 | ✅ |
| 3 | 后端健康检查 | curl /api/health | ✅ |
| 4 | WebSocket 连接 | 浏览器 DevTools Network | 待验证 |
| 5 | 任务提交 | 填任务点击"开始" | 待验证 |
| 6 | Thinking 节点生成 | 等待 thinking 节点出现 | 待验证 |
| 7 | Execution 蓝图生成 | 等待 execution 节点出现 | 待验证 |
| 8 | WebAdapter 截图 | 点击 Web 标签 | 待验证 |
| 9 | 日志写入 logs/ | ls logs/ | ✅ |

---

## 七、已知限制 & 后续优化

| 优先级 | 事项 | 说明 |
|--------|------|------|
| P2 | Docker 容器化 | 当前为裸机部署，建议后续加 Dockerfile |
| P2 | HTTPS/TLS | 当前为 HTTP，生产环境需加反向代理 (nginx/traefik) |
| P2 | 数据库迁移 | 当前用文件系统存储 checkpoints，建议 SQLite/PostgreSQL |
| P2 | CI/CD 流水线 | GitHub Actions 自动测试 + 部署 |
| P2 | 速率限制 | WebSocket 连接数限制 + LLM API QPS 保护 |
| P3 | systemd 服务 | 替代 shell 脚本，支持开机自启 |
| P3 | 日志轮转 | logrotate 配置，防止日志无限增长 |
| P3 | 监控告警 | Prometheus + Grafana 监控 |

---

## 八、故障排查

### 8.1 前端无法打开

```bash
# 检查前端进程
./start_production.sh status
# 检查端口占用
lsof -i :5173
# 查看前端日志
cat logs/frontend.log
```

### 8.2 后端 500 错误

```bash
# 检查后端进程
./start_production.sh status
# 检查 API Key
grep KIMI_API_KEY .env
# 查看后端日志
cat logs/backend.log | tail -50
```

### 8.3 WebAdapter 无法截图

```bash
# 检查 Xvfb
pgrep -a Xvfb
# 检查 DISPLAY 环境变量
echo $DISPLAY
# 手动测试 Playwright
python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); page = b.new_page(); page.goto('https://www.4399.com'); print('OK'); b.close()"
```

### 8.4 429 Too Many Requests

Moonshot API 限流。缓解措施:
- 减少并发任务数
- 增加请求间隔
- 购买更高 QPS 套餐

---

## 九、文件清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `start_production.sh` | 一键启动脚本 | ✅ 已更新 |
| `requirements.txt` | Python 依赖清单 | ✅ 已补全 |
| `.env` | 环境变量配置（无明文 key） | ✅ 已清理 |
| `.env.example` | 配置模板 | ✅ 已创建 |
| `frontend/dist/` | 前端构建产物 | ✅ 已重建 |
| `frontend/src/components/InputScreen.tsx` | 首页（含 API Key 输入） | ✅ 已修改 |
| `backend/websocket/message_router.py` | 后端消息路由（接收 key） | ✅ 已修改 |
| `blueclaw/config.py` | 配置类（支持运行时修改 key） | ✅ 已验证 |
| `blueclaw/llm/client.py` | LLM 客户端（运行时读 Config） | ✅ 已修改 |

---

*文档生成时间: 2026-04-29 20:45*  
*验证截图: `screenshots/verify/v_deploy_01_home.png`*  
*部署脚本: `start_production.sh`*
