# Blueclaw v2.5.0

> Progressive AI Task Execution Engine -- From Thinking to Blueprint, From Execution to Intervention, Complete Closed Loop.

## What's New in v2.5.0

- **IDE Adapter Suite**: Full code modification pipeline with AST analysis (Python/JS/TS/Java), sandbox validation, and auto-apply with Git commit
- **Web Parallel Execution**: Dependency-graph based parallel step executor with semaphore concurrency control
- **Screenshot Optimization Pipeline**: PNG -> resize (LANCZOS 1280px) -> WebP compression (>100x size reduction)
- **Exception Classification & Localization**: 8 typed exception categories with bilingual (CN/EN) user-friendly messages
- **Debug Mode**: Singleton debug controller with timed decorators, section context managers, and optional memory tracing
- **Stability & Integration Tests**: 221 tests covering 50+ state transitions, memory leak detection, resource cleanup, and full pipeline integration

### W2.5 + W3 Updates (2026-04-24)

- **Freeze / Screenshot / Annotation Full Round-trip**: Frontend `FreezeOverlay` → `freeze_request` → `freeze.confirmed` (screenshot) → `submit_annotation` (boxes) → `annotation.submitted`
- **WebAdapter Auto-initialization**: Three entry points (`_maybe_capture_screenshot`, `_execute_blueprint`, `_handle_freeze_request`) ensure Playwright Chromium is ready before screenshot
- **Runtime Auto-attach**: `freeze_request` and `submit_annotation` automatically create `adapter_runtime_manager` runtime if missing
- **ExecutionNode Freeze Button**: Running steps now have a "冻结" button to trigger freeze on demand
- **E2E Verification**: `tests/e2e_freeze_annotation_verify.py` validates the complete freeze-annotation chain (9/9 passed)

## Project Overview

Blueclaw is an AI task execution engine supporting the full lifecycle:

```
User Input
    |
    v
+-----------+     +-----------------+     +-------------+
|  Thinking | --> |   Blueprint     | --> |  Execution  |
| (Clarify) |     | (Steps/DAG)     |     | (Step by step)
+-----------+     +-----------------+     +------+------+
       ^                                          |
       |                                          |
       |          +-----------------+             |
       +--------- |  Intervention   | <-----------+
                  | (Pause/Replan)  |
                  +-----------------+
```

1. **Thinking**: Multi-turn clarification with option trees
2. **Blueprint**: DAG generation with step dependencies and tool bindings
3. **Execution**: Topological step execution with pause/resume/cancel
4. **Intervention**: User-triggered or auto-triggered (>=2 failures) intervention
5. **Freeze & Annotate**: Real-time screenshot + box drawing + annotation submission
6. **Replan**: Context-aware blueprint regeneration

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required: Python 3.10+, Playwright, Pillow, tree-sitter 0.25.2 + language packs

### 2. Start Services

**Option A: Separate terminals**
```bash
# Terminal 1: Backend (WebSocket @ ws://localhost:8006)
python start_backend.py

# Terminal 2: Frontend (Vite @ http://127.0.0.1:5173)
python start_frontend.py
```

**Option B: One-shot test run**
```bash
python start_test.py
```

### 3. Run Adapter Examples

```bash
# Web: Form filling with auto-recovery
python -m blueclaw.adapter.demo.web_recovery

# IDE: Mock code modification loop
python examples/ide/mock_bugfix_loop.py
```

## Architecture

```
blueclawv2/
├── blueclaw/
│   ├── core/           # Execution engine, thinking engine, state sync, replan
│   ├── llm/            # Async LLM client (Kimi/OpenAI via httpx)
│   ├── skills/         # Skill registry
│   ├── api/            # EngineFacade, message protocol
│   └── adapter/        # Execution adapter layer (isolated from backend/adapter/)
│       ├── adapters/   # WebAdapter, IDEAdapter
│       ├── core/       # Screenshot, operation record, checkpoint, replan
│       ├── web/        # Analyzer, locator, executor, validator, recovery, visualization, parallel
│       ├── ide/        # Analyzer, planner, boundary, codemodel, sandbox, applier, loop
│       ├── ui/         # Intervention UIs (Web/Popup/CLI)
│       ├── exceptions.py          # Typed exception hierarchy + JSONL logging
│       ├── error_localization.py  # Bilingual error messages
│       ├── debug.py               # Debug mode controller
│       └── state.py               # State machine + event bus + persistence
├── backend/            # WebSocket service layer
│   ├── websocket/      # Message router with 5 intervention handlers
│   ├── core/           # ExecutionEngine, StateSync, AdapterRuntimeManager
│   └── main.py         # FastAPI + Uvicorn entry
├── frontend/           # React + Vite + Tailwind/shadcn/ui
│   ├── src/components/panels/FreezeOverlay.tsx  # Screenshot + annotation
│   └── src/components/nodes/ExecutionNode.tsx    # Freeze button
├── tests/              # Test suite (221 unit + 3 E2E)
│   ├── e2e_intervention_verify_v3.py
│   ├── e2e_browser_and_annotation_verify.py
│   └── e2e_freeze_annotation_verify.py
├── examples/           # Runnable examples (Web + IDE + Mixed)
├── docs/               # API docs, guides, FAQ
└── scripts/            # Ops tools (detect_masked_errors.py)
```

## Test Suite

```bash
# Full adapter test suite
python -m pytest blueclaw/adapter/tests -v

# E2E golden standard
python tests/e2e/test_beijing_travel_intervention_replan.py --round all

# Cancellation latency benchmark
python tests/test_cancellation_latency.py
```

**Current Status**: 221 passed, 4 warnings (Windows Proactor event loop cleanup)

## Documentation

| Document | Description |
|----------|-------------|
| [docs/API.md](docs/API.md) | Adapter Manager API, data models, freeze/annotation API |
| [docs/websocket_protocol.md](docs/websocket_protocol.md) | WebSocket message types (freeze.confirmed, screenshot, annotation) |
| [docs/GUIDE.md](docs/GUIDE.md) | Quick start, blueprint authoring, adapter usage |
| [docs/FAQ.md](docs/FAQ.md) | Common issues and troubleshooting |
| [FEATURES.md](FEATURES.md) | Core engine feature reference |
| [tests/E2E_VERIFICATION_REPORT.md](tests/E2E_VERIFICATION_REPORT.md) | E2E validation results |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KIMI_API_KEY` | Kimi (Moonshot) API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `USE_SYNC_LLM` | Fallback to synchronous LLM | `0` |

## License

Internal use only.

---

**Version**: v2.5.0 | **Week**: W2.5-W3 | **Tests**: 221 unit + 3 E2E all passed
