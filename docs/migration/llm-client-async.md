# 迁移指南：从 to_thread 到原生 await LLMClient

## 目标读者
所有在 async 上下文中调用 `LLMClient` 的开发者。

## 变更前（旧写法）
```python
import asyncio
from blueclaw.llm import LLMClient, Message

response = await asyncio.to_thread(
    LLMClient().chat_completion,
    [
        Message(role="system", content="..."),
        Message(role="user", content="...")
    ]
)
```

## 变更后（新写法）
```python
from blueclaw.llm import LLMClient, Message

response = await LLMClient().chat_completion(
    [
        Message(role="system", content="..."),
        Message(role="user", content="...")
    ]
)
```

## 迁移检查清单
- [ ] 删除 `import asyncio`（如果仅用于 `asyncio.to_thread`）
- [ ] 删除 `asyncio.to_thread(LLMClient().chat_completion, ...)` 包装
- [ ] 确保调用所在的函数是 `async def`
- [ ] 确保调用前有 `await`

## 常见错误
### 错误 1：忘记 `await`
```python
# ❌ 错误
response = LLMClient().chat_completion([...])

# ✅ 正确
response = await LLMClient().chat_completion([...])
```
运行时会出现 `RuntimeWarning: coroutine 'LLMClient.chat_completion' was never awaited`。

### 错误 2：在同步函数中调用
```python
# ❌ 错误
def some_sync_func():
    response = await LLMClient().chat_completion([...])

# ✅ 正确
async def some_async_func():
    response = await LLMClient().chat_completion([...])
```

### 错误 3：需要同步上下文怎么办？
如果确实无法使用 async（例如后台脚本），请使用已弃用的同步接口：
```python
response = LLMClient().chat_completion_sync([...])
```
注意会打印 `DeprecationWarning`。

## 快速扫描未迁移代码
```bash
# 查找项目中仍使用 to_thread 包装 LLMClient 的代码
grep -rn "asyncio.to_thread.*LLMClient" blueclaw backend
```
若返回为空，说明迁移完成。
