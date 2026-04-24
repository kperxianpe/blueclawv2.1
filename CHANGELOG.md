# Changelog

All notable changes to Blueclaw v2 are documented in this file.

## [v2.5.0] - 2026-04-04

### Added

#### IDE Adapter (Week 26-27)
- `ide/analyzer.py`: Tree-sitter + AST-based codebase analyzer for Python/JS/TS/Java
- `ide/planner.py`: Architecture planner generating `ModificationPlan` with dependency graph
- `ide/boundary.py`: File boundary checker with allow/deny/protected glob rules
- `ide/codemodel.py`: `KimiCodeClient` via openai.AsyncOpenAI SDK with unified diff parsing
- `ide/sandbox.py`: Local temp-directory sandbox with syntax/test/static analysis validation
- `ide/applier.py`: `IncrementApplier` applying diffs with auto Git commit and rollback
- `ide/loop.py`: `ModificationLoop` with CodeModel -> Sandbox -> Retry -> Apply pipeline
- 56 IDE tests covering mock and real Kimi API integration

#### Web Parallel Execution (Week 28)
- `web/parallel.py`: `ParallelExecutor` with DAG topological level grouping + semaphore concurrency
- `analyze_parallel_potential()`: Estimated speedup analysis for star/linear DAGs

#### Screenshot Pipeline (Week 28)
- `core/screenshot.py`: `resize()` (LANCZOS, max 1280px) + `compress()` (PNG->WebP) + `optimize()`
- Achieves >100x size reduction vs raw PNG

#### E2E & Performance Tests (Week 28)
- `tests/e2e/`: End-to-end tests with Playwright headless Chromium
- `tests/performance/`: Benchmark tests for cancellation latency, screenshot pipeline, parallel execution

#### Error Handling & Stability (Week 29)
- `exceptions.py`: 8 typed exception categories (`SandboxAdapterException`, `PageLoadAdapterException`, `ResourceExhaustedAdapterException`, `RetryExhaustedException`)
- `error_localization.py`: Bilingual (CN/EN) error templates and repair suggestions
- `debug.py`: Singleton `DebugMode` with `@timed` decorator, `debug_section` context manager, memory tracing
- `tests/stability/`: 50+ state transition tests, memory leak detection, resource cleanup tests
- `tests/integration/`: Full pipeline integration and edge case tests

#### Documentation & Examples (Week 30)
- `docs/API.md`: Complete public API documentation
- `docs/GUIDE.md`: Quick start, blueprint authoring, Web/IDE adapter usage
- `docs/FAQ.md`: 15+ common issues with solutions
- `examples/web/`: 5 runnable Web scenarios
- `examples/ide/`: 5 runnable IDE scenarios
- `examples/mixed/`: 1 mixed Web+IDE scenario

### Changed
- Test directory reorganized into `tests/{acceptance,core,e2e,ide,integration,performance,stability,web}/`
- `README.md` updated to v2.5.0 with architecture diagram and quick start

### Fixed
- Windows Proactor event loop cleanup warnings mitigated
- Playwright process leak on Windows managed via `taskkill` between runs

### Test Counts by Module

| Module | Count |
|--------|-------|
| acceptance | 6 |
| core | 52 |
| e2e | 12 |
| ide | 56 |
| integration | 17 |
| performance | 8 |
| stability | 15 |
| web | 55 |
| **Total** | **221** |

## [v2.0.0] - 2026-02-XX

### Added
- Async LLM client with `httpx.AsyncClient`
- `CancellationToken` with tree-structured propagation
- `StepExecutionError` with recoverable vs non-recoverable classification
- WebSocket message router (`MessageRouter`)
- State sync manager (`StateSyncManager`)
- Tool registry with auto-binding rules
- Replan engine
- Masked error detector (`scripts/detect_masked_errors.py`)

---

**Versioning**: Semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Breaking architecture changes
- MINOR: New features (weekly iterations)
- PATCH: Bug fixes and docs
