# Blueclaw Adapter FAQ

## General

### Q: What Python version is required?
**A**: Python 3.10 or higher. The project uses modern typing features (`Literal`, `TypedDict`, etc.) and `asyncio` patterns.

### Q: Can I use the adapter without the full Blueclaw backend?
**A**: Yes. The adapter layer (`blueclaw.adapter`) is designed to be self-contained. You can import `AdapterManager`, `WebExecutor`, or `ModificationLoop` directly without starting the WebSocket backend.

### Q: Where do I put my API key?
**A**: Set the `KIMI_API_KEY` environment variable. The `KimiCodeClient` reads it automatically. Alternatively, pass it explicitly:
```python
client = KimiCodeClient(api_key="your-key-here")
```

---

## Web Adapter

### Q: Playwright fails to launch browser on Windows?
**A**: Run `playwright install chromium` to download browser binaries. If you see permission errors, run PowerShell as Administrator.

### Q: How do I run in headed mode for debugging?
**A**: Set `headless=False` in `AdapterConfig` or launch the browser directly:
```python
browser = await p.chromium.launch(headless=False)
```

### Q: Element not found even though I can see it?
**A**: Common causes:
1. **Timing**: Add a `wait` step before the action, or increase `AdapterConfig.timeout`.
2. **Distraction filtering**: The element might be marked as a distraction. Check `analysis.distractions` after `WebAnalyzer.analyze(page)`.
3. **Selector stale**: The page dynamically changed. Use `fallback_selectors` in `RecoveryConfig`.

### Q: How do I handle CAPTCHA or login walls?
**A**: The adapter does not bypass CAPTCHA. For login walls, use a `navigate` step to a pre-authenticated session, or inject cookies via Playwright before execution.

### Q: Screenshot files are too large?
**A**: The screenshot pipeline automatically resizes to 1280px max and compresses to WebP (quality 70). If you need smaller files, lower the quality:
```python
screenshot = PlaywrightScreenshot()
screenshot.optimize(data, quality=50, max_dimension=800)
```

### Q: Playwright process leaks on Windows?
**A**: This is a known Windows issue. Between test runs, run:
```powershell
taskkill /F /IM node.exe
```
The test suite automatically handles this in tear-down.

### Q: Can I run steps in parallel?
**A**: Yes. Use `ParallelExecutor` with dependency-aware grouping:
```python
from blueclaw.adapter.web.parallel import ParallelExecutor
await ParallelExecutor().execute_parallel(steps, executor, max_concurrency=3)
```
Steps with dependencies will wait; independent steps run concurrently.

---

## IDE Adapter

### Q: Tree-sitter parser fails to import?
**A**: Ensure you have the correct tree-sitter version and language packs:
```bash
pip install tree-sitter==0.25.2 tree-sitter-python tree-sitter-javascript tree-sitter-typescript tree-sitter-java
```

### Q: The modification loop keeps failing validation?
**A**: Check the `result.debug_log` for detailed per-check output:
```python
for line in result.debug_log:
    print(line)
```
Common causes: syntax errors in generated diffs, missing imports, test assertions failing.

### Q: How do I disable sandbox validation?
**A**: Pass a disabled config:
```python
sandbox = SandboxValidator(project_path=".", config=SandboxConfig(enabled=False))
```
This skips all checks and returns success immediately.

### Q: Can I use a different LLM provider?
**A**: Yes. Subclass `BaseCodeModelClient` and implement `generate_code_changes()`:
```python
class MyCodeClient(BaseCodeModelClient):
    async def generate_code_changes(self, task_description, file_context, constraints=None):
        # Call your LLM API here
        return CodeModelResponse(success=True, diffs=[...])
```

### Q: How do I prevent the adapter from modifying certain files?
**A**: Use `BoundaryChecker` with `protected` rules:
```python
from blueclaw.adapter.ide.boundary import BoundaryChecker, BoundaryRule
checker = BoundaryChecker([
    BoundaryRule(rule_type="protected", pattern="**/*.secret"),
    BoundaryRule(rule_type="deny", pattern="**/node_modules/**"),
])
```

---

## Error Handling

### Q: What does "RetryExhaustedAdapterException" mean?
**A**: All automatic recovery strategies (retry, fallback selectors, rollback) failed. The task is paused for human intervention if `pause_on_failure=True`.

### Q: How do I get Chinese error messages?
**A**: Use `localize_error`:
```python
from blueclaw.adapter.error_localization import localize_error
msg = localize_error("network", str(e), lang="zh")
```

### Q: Where are error logs stored?
**A**: `blueclaw/adapter/logs/adapter_exceptions.jsonl`. Each entry is a JSON line with category, message, timestamp, context, and stack trace.

---

## Performance & Stability

### Q: How do I enable debug mode?
**A**: 
```python
from blueclaw.adapter.debug import DebugMode
DebugMode().enable(trace_memory=True)
```
This enables timed function logging and optional `tracemalloc` memory tracking.

### Q: Cancellation latency is high?
**A**: The baseline is ~107ms. If you observe >200ms, check:
1. Is the event loop congested with blocking I/O?
2. Are Playwright screenshots taking too long? Reduce resolution or disable screenshots.

### Q: Memory usage keeps growing?
**A**: Enable memory tracing and take snapshots between tasks:
```python
DebugMode().enable(trace_memory=True)
# ... run tasks ...
print(DebugMode().get_memory_snapshot())
```
Operation logs and checkpoints are the primary memory consumers. Call `.clear()` on `OperationLog` periodically if running long-lived processes.

---

## Integration

### Q: How do I convert a Core blueprint to Adapter blueprint?
**A**: Use the static method:
```python
from blueclaw.adapter import AdapterManager
adapter_blueprint = AdapterManager.from_core_blueprint(core_dict)
```

### Q: Can I subscribe to state changes?
**A**: Yes, via `EventBus`:
```python
from blueclaw.adapter.state import EventBus
bus = EventBus()
bus.subscribe("state.changed", lambda payload: print(f"State changed: {payload}"))
```

### Q: Frontend WebSocket port conflicts?
**A**: Kill lingering Node processes:
```powershell
taskkill /F /IM node.exe
```
Or change the port in `start_frontend.py`.
