# ADR-001: LLMClient 异步化重构（urllib → httpx.AsyncClient）

## 状态
已接受 (Accepted)

## 背景
原 `blueclaw/llm/client.py` 使用 `urllib.request.urlopen` 进行同步 HTTP 调用。在 async WebSocket 后端中，该调用通过 `asyncio.to_thread(...)` 包装，但带来两个致命问题：
1. **取消信号无法穿透**：`cancel_execution()` 只能标记取消，底层线程仍会继续阻塞最长 60s，造成资源泄漏和事件循环饥饿。
2. **新开发者极易踩坑**：任何新增的 async 调用点若遗漏 `to_thread` 包装，就会直接阻塞整个事件循环。

## 决策
将 `LLMClient` 的核心 HTTP 层从 `urllib.request` 迁移至 `httpx.AsyncClient`，实现原生异步、可取消、连接池复用。

### 候选方案对比
| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. httpx.AsyncClient** (选中) | API 与 requests 高度相似；内置连接池；原生支持 async/await；取消信号可直接穿透 | 需要新增依赖（已满足，环境已有 httpx 0.23.3） |
| **B. aiohttp** | 性能优秀；社区成熟 | API 与 requests 差异较大；学习成本略高 |
| **C. 保留 urllib + 线程池** | 零依赖变动 | 无法根治取消穿透问题；技术债务持续累积 |

## 实现要点
1. `chat_completion()` 改为 `async def`，内部使用 `await client.post(...)`。
2. 懒加载 `httpx.AsyncClient`，配置 `Limits(max_connections=100)` 与 `Timeout(60.0, connect=5.0, read=60.0)`。
3. 保留 `chat_completion_sync()` 作为同步回退（标记 `@deprecated`），供后台脚本等非 async 上下文紧急使用。
4. Feature Flag `USE_SYNC_LLM=1` 用于紧急回退。

## 取消信号实现细节
`httpx.AsyncClient.post()` 返回的 coroutine 可被 `asyncio.CancelledError` 直接中断。当 `ExecutionEngine.cancel_execution()` 触发时：
1. `CancellationToken.is_cancelled` 被置为 `True`。
2. 主 blueprint task 收到 `cancel()`。
3. `await client.post(...)` 抛出 `asyncio.CancelledError`，立即向上传播。
4. `_execute_step` 捕获后标记 `SKIPPED` 并清理资源。

实测取消延迟：**~107ms**（目标 < 200ms）。

## 影响范围
- `blueclaw/llm/client.py`：核心重构
- `blueclaw/core/thinking_engine.py`：移除 `asyncio.to_thread`
- `blueclaw/core/execution_engine.py`：移除 `asyncio.to_thread`
- `backend/vis/vlm.py`：补 `await`

## 后续行动
- 在 Grafana 新增面板：`LLM Cancel Latency`
- 禁止在新代码中重新引入同步阻塞 HTTP 调用
