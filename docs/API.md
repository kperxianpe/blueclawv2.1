# Blueclaw Adapter API Documentation

## Overview

The `blueclaw.adapter` module is the execution adapter layer that routes `ExecutionBlueprint` from the Core engine to external target environments (Web browser / IDE editor).

---

## 1. AdapterManager

**Module**: `blueclaw.adapter.manager`

Entry point for executing blueprints and managing lifecycle.

### Constructor

```python
manager = AdapterManager()
```

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `execute` | `async execute(blueprint: ExecutionBlueprint) -> ExecutionResult` | Execute a blueprint through the appropriate adapter |
| `pause` | `async pause(task_id: str) -> None` | Pause execution (valid from executing/planning/validating) |
| `resume` | `async resume(task_id: str) -> None` | Resume from paused state |
| `cancel` | `async cancel(task_id: str) -> None` | Cancel and cleanup |
| `get_adapter` | `get_adapter(adapter_type: str) -> BaseAdapter` | Get WebAdapter or IDEAdapter |
| `from_core_blueprint` | `staticmethod from_core_blueprint(core_blueprint: dict) -> ExecutionBlueprint` | Convert Core dict to Adapter Pydantic model |

### Example

```python
from blueclaw.adapter import AdapterManager, ExecutionBlueprint, ExecutionStep
from blueclaw.adapter.models import ActionDefinition, TargetDescription

manager = AdapterManager()

blueprint = ExecutionBlueprint(
    task_id="demo-001",
    adapter_type="web",
    steps=[
        ExecutionStep(
            step_id="s1",
            name="Open search page",
            action=ActionDefinition(
                type="navigate",
                target=TargetDescription(semantic="https://example.com"),
            ),
        ),
    ],
)

result = await manager.execute(blueprint)
print(result.success, result.output)
```

---

## 2. Data Models

**Module**: `blueclaw.adapter.models`

### ExecutionBlueprint

```python
class ExecutionBlueprint(BaseModel):
    task_id: str
    adapter_type: Literal["web", "ide"]
    steps: List[ExecutionStep]
    config: AdapterConfig = AdapterConfig()
```

### ExecutionStep

```python
class ExecutionStep(BaseModel):
    step_id: str
    name: str
    action: ActionDefinition
    dependencies: List[str] = []        # step_ids this step depends on
    validation: Optional[ValidationRule] = None
```

### ActionDefinition

```python
class ActionDefinition(BaseModel):
    type: Literal[
        "navigate", "click", "input", "scroll", "screenshot", "select",
        "execute_command", "open_file", "edit_file", "select_text", "wait"
    ]
    target: Optional[TargetDescription] = None
    params: Dict[str, Any] = {}
```

### TargetDescription

```python
class TargetDescription(BaseModel):
    semantic: str = ""          # Human-readable description
    selector: Optional[str] = None    # CSS selector / XPath
    coordinates: Optional[Dict[str, int]] = None   # {x, y} fallback
```

### ValidationRule

```python
class ValidationRule(BaseModel):
    type: Literal["presence", "text_contains", "return_code", "custom", "url_match", "visual_match"]
    expected: Any
```

### AdapterConfig

```python
class AdapterConfig(BaseModel):
    headless: bool = True
    timeout: int = Field(default=30, ge=1)
    extra: Dict[str, Any] = {}
```

### ExecutionResult (Union)

```python
WebExecutionResult(
    success: bool,
    duration_ms: float,
    output: str,
    screenshot: Optional[str] = None,
    error_context: Optional[Dict[str, Any]] = None,
)

IDEExecutionResult(
    success: bool,
    duration_ms: float,
    output: str,
    modified_files: List[str] = [],
    error_context: Optional[Dict[str, Any]] = None,
)
```

---

## 3. Web Adapter

**Module**: `blueclaw.adapter.web.*`

### WebExecutor

```python
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot

executor = WebExecutor(
    screenshot_capture=PlaywrightScreenshot(),
    validator=WebValidator(),
    recovery_controller=RecoveryController(...),
    visualizer=CanvasMindVisualizer(),
    web_checkpoint_manager=WebCheckpointManager(...),
)

result = await executor.execute_step(step, page, blueprint_id="task-001")
# result.status: "success" | "failed" | "skipped" | "intervention_needed"
```

### WebAnalyzer

```python
from blueclaw.adapter.web.analyzer import WebAnalyzer

analyzer = WebAnalyzer(screenshot_capture=PlaywrightScreenshot())
analysis = await analyzer.analyze(page)
# analysis.elements: List[WebElement]
# analysis.distractions: List[WebElement]
```

### WebLocator

```python
from blueclaw.adapter.web.locator import WebLocator

locator = WebLocator()
result = await locator.locate("Submit button", analysis.elements, page)
# result.strategy: "semantic" | "selector" | "coordinate" | "fallback"
```

### WebValidator

Validation types supported:

| Type | Expected Value | Description |
|------|---------------|-------------|
| `url_match` | regex string | Match current page URL |
| `presence` | `True` or selector dict | Element exists on page |
| `text_contains` | `{"selector": "...", "text": "..."}` or plain string | Text containment check |
| `visual_match` | baseline image bytes | SSIM-based screenshot comparison |
| `custom` | callable | User-defined sync/async function |
| `return_code` | any | Web context placeholder (always passes) |

### RecoveryController

```python
from blueclaw.adapter.web.recovery import RecoveryController, RecoveryConfig

recovery = RecoveryController(
    web_checkpoint_manager=cp_mgr,
    config=RecoveryConfig(
        max_retries=2,
        retry_backoff_ms=500,
        fallback_selectors=["#btn-new", "button[type='submit']"],
        enable_rollback=True,
        pause_on_failure=False,
    ),
)
```

### ParallelExecutor

```python
from blueclaw.adapter.web.parallel import ParallelExecutor

parallel = ParallelExecutor()
await parallel.execute_parallel(steps, executor, max_concurrency=3)

speedup = parallel.analyze_parallel_potential(steps)
```

---

## 4. IDE Adapter

**Module**: `blueclaw.adapter.ide.*`

### CodebaseAnalyzer

```python
from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer

analyzer = CodebaseAnalyzer(project_path="/path/to/project")
analysis = analyzer.analyze(max_files=500)
# analysis.files: List[FileAnalysis]
# analysis.dependencies: List[DependencyEdge]
# analysis.languages: Dict[str, int]
```

### ModificationLoop

```python
from blueclaw.adapter.ide.loop import ModificationLoop
from blueclaw.adapter.ide.codemodel import KimiCodeClient
from blueclaw.adapter.ide.sandbox import SandboxValidator

loop = ModificationLoop(
    code_model=KimiCodeClient(api_key=os.getenv("KIMI_API_KEY")),
    sandbox=SandboxValidator(project_path="/path/to/project"),
    applier=IncrementApplier(project_path="/path/to/project"),
    config=LoopConfig(max_iterations=3, enable_auto_apply=False),
)

result = await loop.run(
    task_description="Fix divide-by-zero bug in calculate()",
    file_context={"math.py": "def calculate(x): return 100 / x\n"},
)
# result.success: bool
# result.iterations: int
# result.final_validation: SandboxValidationResult
# result.paused_for_human: bool
```

### SandboxValidator

```python
from blueclaw.adapter.ide.sandbox import SandboxValidator, SandboxConfig

sandbox = SandboxValidator(
    project_path="/path/to/project",
    config=SandboxConfig(
        enabled=True,
        check_syntax=True,
        check_tests=True,
        check_static_analysis=False,
        timeout_seconds=60,
    ),
)
result = await sandbox.validate(diffs)
# result.success: bool
# result.checks: List[ValidationCheck]
```

### IncrementApplier

```python
from blueclaw.adapter.ide.applier import IncrementApplier

applier = IncrementApplier(project_path="/path/to/project")
apply_result = applier.apply_diffs(diffs, auto_commit=True, commit_message="fix: bug")
applier.rollback(pre_apply_head=apply_result.pre_apply_head)
```

---

## 5. State Machine

**Module**: `blueclaw.adapter.state`

### AdapterState

```python
class AdapterState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
```

### StateMachine

```python
from blueclaw.adapter.state import StateMachine, AdapterState, EventBus

event_bus = EventBus()
event_bus.subscribe("state.changed", lambda payload: print(payload))

sm = StateMachine(task_id="task-001", event_bus=event_bus)
await sm.transition(AdapterState.EXECUTING, {"action": "start"})
history = sm.get_history()
```

---

## 6. Exception Hierarchy

**Module**: `blueclaw.adapter.exceptions`

```
AdapterException (base)
  ├── NetworkAdapterException
  ├── LocatorAdapterException
  ├── ExecutionAdapterException
  ├── ValidationAdapterException
  ├── TimeoutAdapterException
  ├── SandboxAdapterException
  ├── PageLoadAdapterException
  ├── ResourceExhaustedAdapterException
  └── RetryExhaustedAdapterException
```

### classify_error

```python
from blueclaw.adapter.exceptions import classify_error

typed_exc = classify_error(raw_exception, context={"step_id": "s1"})
# Returns appropriate AdapterException subclass
```

All exceptions automatically log structured JSONL to `blueclaw/adapter/logs/adapter_exceptions.jsonl`.

---

## 7. Error Localization

**Module**: `blueclaw.adapter.error_localization`

```python
from blueclaw.adapter.error_localization import localize_error, get_error_suggestion

message = localize_error("network", "Connection refused", lang="zh")
# "网络连接失败: Connection refused\n建议: 检查网络连接，稍后重试。"

suggestion = get_error_suggestion("locator", lang="zh")
# "1. 等待页面完全加载...\n2. 更新 CSS/XPath 选择器..."
```

---

## 8. Debug Mode

**Module**: `blueclaw.adapter.debug`

```python
from blueclaw.adapter.debug import DebugMode, timed, debug_section

DebugMode().enable(trace_memory=True)

@timed
async def my_func():
    with debug_section("analyze"):
        pass

snapshot = DebugMode().get_memory_snapshot()
# "Current: 12.34MB, Peak: 56.78MB"
```

---

## 9. WebSocket Protocol (CanvasMind)

**Module**: `blueclaw.adapter.models`

```python
class CanvasMindMessage(BaseModel):
    adapterType: Literal["web", "ide"]
    taskId: str
    currentStep: int
    totalSteps: int
    state: Literal["idle", "planning", "executing", "validating", "paused", "completed", "failed"]
    operation: Optional[Dict[str, Any]] = None
```

### InterventionEvent

```python
class InterventionEvent(BaseModel):
    task_id: str
    checkpoint_seq: int
    type: Literal["text_hint", "click_correction", "stop", "replan"]
    payload: Dict[str, Any] = {}
    timestamp: Optional[int] = None
```

---

## 10. Freeze / Screenshot / Annotation API

**Module**: `backend.websocket.message_router`

### Freeze Flow

```
Frontend                              Backend
  | ------ freeze_request ------------> |
  |                                     | (1) Find blueprint
  |                                     | (2) Screenshot via WebAdapter
  |                                     | (3) Freeze runtime state
  | <---- freeze.confirmed ------------ | (4) Push screenshot + freezeToken
  |                                     |
  | (User draws boxes on screenshot)    |
  |                                     |
  | ------ submit_annotation ---------> | (5) Save boxes to annotations
  |                                     | (6) Unfreeze runtime
  | <---- annotation.submitted -------- | (7) Return saved box IDs
  | <---- status_update --------------- | (8) Push resumed status
```

### Message Types

| Direction | Type | Key Fields |
|-----------|------|------------|
| F → B | `freeze_request` | `task_id`, `step_id`, `reason?` |
| B → F | `freeze.confirmed` | `adapterId`, `stepId`, `screenshot` (base64 PNG), `freezeToken` |
| F → B | `submit_annotation` | `task_id`, `step_id`, `annotation?`, `boxes[]`, `freeze_token?` |
| B → F | `annotation.submitted` | `step_id`, `annotation`, `boxes[{id, rect, label}]` |
| B → F | `screenshot` | `adapterId`, `stepId`, `image` (base64), `timestamp` |

### Box Format

```python
{
    "x": 100,       # top-left x in natural image pixels
    "y": 200,       # top-left y in natural image pixels
    "w": 300,       # width in pixels
    "h": 150,       # height in pixels
    "label": "Button"  # optional
}
```

### Frontend Components

| Component | Path | Purpose |
|-----------|------|---------|
| `FreezeOverlay` | `frontend/src/components/panels/FreezeOverlay.tsx` | Screenshot display + box drawing + text input + submit |
| `ExecutionNode` | `frontend/src/components/nodes/ExecutionNode.tsx` | Shows "Freeze" button when step is running |
| `RealtimeProvider` | `frontend/src/components/RealtimeProvider.tsx` | Handles `freeze.confirmed` and `screenshot` WS messages |

---

## Error Code Reference

| Category | HTTP-style Code | Description |
|----------|----------------|-------------|
| network | ADAPTER_NET_001 | Connection failure / DNS / reset |
| locator | ADAPTER_LOC_001 | Element not found / selector stale |
| execution | ADAPTER_EXEC_001 | Generic execution failure |
| validation | ADAPTER_VAL_001 | Step validation failure |
| timeout | ADAPTER_TMO_001 | Operation exceeded timeout |
| sandbox | ADAPTER_SBX_001 | Sandbox container crash |
| page_load | ADAPTER_PGL_001 | 404/500/SSL error |
| resource_exhausted | ADAPTER_RES_001 | Memory/disk/CPU limit |
| retry_exhausted | ADAPTER_RTY_001 | All recovery strategies failed |
