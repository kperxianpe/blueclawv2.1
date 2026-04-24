# Blueclaw Adapter Usage Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Writing Blueprints](#writing-blueprints)
3. [Web Adapter Usage](#web-adapter-usage)
4. [IDE Adapter Usage](#ide-adapter-usage)
5. [Intervention Flow](#intervention-flow)
6. [Custom Validation Rules](#custom-validation-rules)

---

## 1. Quick Start

### Prerequisites

```bash
pip install pydantic playwright pillow tree-sitter tree-sitter-python tree-sitter-javascript
playwright install chromium
```

### Minimal Web Example

```python
import asyncio
from blueclaw.adapter import AdapterManager, ExecutionBlueprint, ExecutionStep
from blueclaw.adapter.models import ActionDefinition, TargetDescription

async def main():
    manager = AdapterManager()

    blueprint = ExecutionBlueprint(
        task_id="quick-web-001",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="s1",
                name="Open example.com",
                action=ActionDefinition(
                    type="navigate",
                    target=TargetDescription(semantic="https://example.com"),
                ),
            ),
            ExecutionStep(
                step_id="s2",
                name="Take screenshot",
                action=ActionDefinition(type="screenshot"),
            ),
        ],
    )

    result = await manager.execute(blueprint)
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_ms}ms")

asyncio.run(main())
```

### Minimal IDE Example

```python
import asyncio
from blueclaw.adapter.ide.loop import ModificationLoop
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator

async def main():
    loop = ModificationLoop(
        code_model=MockCodeModelClient(),
        sandbox=SandboxValidator(project_path="."),
    )
    result = await loop.run(
        task_description="Add a hello() function",
        file_context={"main.py": "# placeholder\n"},
    )
    print(f"Success: {result.success}, Iterations: {result.iterations}")

asyncio.run(main())
```

---

## 2. Writing Blueprints

### Blueprint Structure

A blueprint is a declarative description of what to do. It contains:

- `task_id`: Unique identifier
- `adapter_type`: `"web"` or `"ide"`
- `steps`: Ordered list of execution steps
- `config`: Optional execution parameters

### Step Dependencies

Use `dependencies` to build a DAG. Steps with no dependencies run first (or in parallel if using `ParallelExecutor`).

```python
steps = [
    ExecutionStep(step_id="login", name="Login", action=...),
    ExecutionStep(step_id="search", name="Search", action=..., dependencies=["login"]),
    ExecutionStep(step_id="export", name="Export", action=..., dependencies=["search"]),
]
```

### Action Types Reference

| Type | Target Required | Params | Description |
|------|----------------|--------|-------------|
| `navigate` | semantic (URL) | - | Load a page |
| `click` | semantic / selector | - | Click an element |
| `input` | semantic / selector | `{"value": "..."}` | Fill an input field |
| `scroll` | - | `{"dx": 0, "dy": 300}` | Scroll the page |
| `select` | semantic / selector | `{"value": "..."}` | Select a dropdown option |
| `screenshot` | - | - | Capture page screenshot |
| `wait` | - | `{"ms": 1000}` | Wait for N milliseconds |
| `execute_command` | semantic (command) | - | Execute shell command (IDE) |
| `open_file` | semantic (path) | - | Open a file (IDE) |
| `edit_file` | semantic (path) | `{"diff": "..."}` | Apply diff (IDE) |

### Validation Rules

Attach validation to any step to verify execution outcome:

```python
ExecutionStep(
    step_id="s1",
    name="Verify login success",
    action=ActionDefinition(type="click", target=TargetDescription(selector="#login-btn")),
    validation=ValidationRule(
        type="text_contains",
        expected={"selector": "#welcome", "text": "Welcome"},
    ),
)
```

---

## 3. Web Adapter Usage

### Full Web Execution Pipeline

The Web adapter runs the following pipeline for each step:

```
Inject overlay + progress bar
      |
  Pre-screenshot
      |
  Analyze page (extract elements)
      |
  Detect distractions (ads/popups)
      |
  Locate target element
      |
  Execute Playwright action
      |
  Post-screenshot (WebP compressed)
      |
  Validate (if rule attached)
      |
  Auto-recover (if failed)
      |
  Save checkpoint + operation record
```

### Running with Recovery

```python
from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.web.recovery import RecoveryController, RecoveryConfig
from blueclaw.adapter.web.checkpoint import WebCheckpointManager
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot

cp_mgr = WebCheckpointManager(base_dir="./checkpoints")
recovery = RecoveryController(
    web_checkpoint_manager=cp_mgr,
    config=RecoveryConfig(
        max_retries=2,
        fallback_selectors=["#btn-new", "button[type='submit']"],
        enable_rollback=True,
    ),
)
executor = WebExecutor(
    screenshot_capture=PlaywrightScreenshot(),
    recovery_controller=recovery,
)
```

### Parallel Execution

```python
from blueclaw.adapter.web.parallel import ParallelExecutor

parallel = ParallelExecutor()
await parallel.execute_parallel(steps, executor, max_concurrency=3)
```

Steps are grouped by topological levels. All steps in the same level execute concurrently (up to `max_concurrency`).

---

## 4. IDE Adapter Usage

### Code Analysis

```python
from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer

analyzer = CodebaseAnalyzer(project_path=".")
analysis = analyzer.analyze(max_files=500)

for file in analysis.files:
    print(f"{file.path}: {file.language}, {len(file.symbols)} symbols")

for dep in analysis.dependencies:
    print(f"{dep.source} -> {dep.target} ({dep.edge_type})")
```

### Modification Loop (with Real LLM)

```python
import os
from blueclaw.adapter.ide.loop import ModificationLoop, LoopConfig
from blueclaw.adapter.ide.codemodel import KimiCodeClient
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier

loop = ModificationLoop(
    code_model=KimiCodeClient(api_key=os.getenv("KIMI_API_KEY")),
    sandbox=SandboxValidator(project_path=".", config=...),
    applier=IncrementApplier(project_path="."),
    config=LoopConfig(
        max_iterations=3,
        enable_auto_apply=False,   # Set True to auto-commit on success
        pause_on_failure=True,     # Pause for human review if all retries fail
    ),
)

result = await loop.run(
    task_description="Refactor the calculate function to handle edge cases",
    file_context={"math.py": open("math.py").read()},
)

if result.success:
    print(f"Validation passed in {result.iterations} iterations")
    if result.final_apply:
        print(f"Committed: {result.final_apply.commit_hash}")
else:
    print(f"Failed: {result.error}")
    if result.paused_for_human:
        print("Paused for human intervention")
```

### File Boundary Protection

```python
from blueclaw.adapter.ide.boundary import BoundaryChecker, BoundaryRule

checker = BoundaryChecker([
    BoundaryRule(rule_type="protected", pattern="**/*.secret", description="Secret files"),
    BoundaryRule(rule_type="deny", pattern="**/vendor/**", description="Third-party code"),
    BoundaryRule(rule_type="allow", pattern="src/**/*.py", description="Main source"),
])

result = checker.check(["src/main.py", "config.secret"])
print(result.allowed)       # False
print(result.violations)    # ["config.secret"]
```

---

## 5. Intervention Flow

### Trigger Conditions

- **User-triggered**: Frontend sends `execution.intervene` message
- **Auto-triggered**: Blueprint accumulates >= 2 failed steps
- **Step-level**: Step explicitly requests confirmation

### Intervention Types

| Type | Description |
|------|-------------|
| `retry` | Retry current step with modified parameters |
| `skip` | Skip current step and continue |
| `replan` | Generate new blueprint from checkpoint + context |
| `abort` | Cancel entire task |

### CLI Intervention Example

```python
from blueclaw.adapter.ui.intervention.cli import CliInterventionUI

ui = CliInterventionUI()
choice = await ui.present(
    task_id="task-001",
    checkpoint_seq=3,
    reason="Element not found after 2 retries",
    options=["retry", "skip", "replan", "abort"],
)
print(f"User chose: {choice}")
```

---

## 6. Custom Validation Rules

### Custom Function Validator

```python
from blueclaw.adapter.web.validator import WebValidator

async def custom_check(page):
    count = await page.locator(".item").count()
    return count >= 5

validator = WebValidator()
result = await validator.validate(
    page,
    ValidationRule(type="custom", expected=custom_check),
)
```

Custom validators can be sync or async callables that receive the Playwright `page` object and return a truthy/falsy value.

### Visual Match Validator

```python
import pathlib

baseline = pathlib.Path("baseline.png").read_bytes()

validator = WebValidator()
result = await validator.validate(
    page,
    ValidationRule(type="visual_match", expected=baseline),
)
# Uses OpenCV SSIM comparison; threshold defaults to 0.85
```
