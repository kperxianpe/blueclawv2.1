# Blueclaw WebSocket Protocol v2.5

## Overview

This document defines the bidirectional WebSocket message protocol between the Blueclaw frontend (React) and backend (FastAPI + Uvicorn).

- **Connection URL**: `ws://localhost:8006/ws`
- **Message Format**: JSON with `type`, `payload`, `timestamp`, and `message_id` fields
- **Transport**: WebSocket (per-message JSON)

---

## Common Message Structure

```typescript
interface WebSocketMessage {
  type: string;           // Message type (see tables below)
  payload: Record<string, any>;
  timestamp: number;      // Unix timestamp in milliseconds
  message_id: string;     // UUID v4
}
```

---

## Backend → Frontend Messages

### Task Lifecycle

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `task.started` | Task created and thinking initialized | `{ task_id: string, user_input: string }` |
| `task.interrupted` | Task was interrupted | `{ task_id: string }` |

### Thinking Phase

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `thinking.node_created` | Root thinking node generated | `{ node: ThinkingNode, options: Option[], allow_custom: boolean, previous_node_id: null }` |
| `thinking.node_selected` | Child thinking node generated after selection | `{ node: ThinkingNode, options: Option[], allow_custom: boolean, previous_node_id: string }` |
| `thinking.option_selected` | User/AI selected an option | `{ option_id: string, current_node_id: string, has_more: boolean, final_path?: PathItem[] }` |
| `thinking.custom_input_received` | User submitted custom input | `{ current_node_id: string, custom_input: string, has_more: boolean }` |
| `thinking.completed` | Thinking chain finished (all layers resolved) | `{ final_path: PathItem[] }` |
| `thinking.converged` | **(NEW)** Thinking converged, auto-transitioning to execution | `{ final_path: PathItem[], auto_transition: true, message: string }` |
| `thinking.execution_confirmed` | Manual execution confirmation response | `{ task_id: string, blueprint_id: string, blueprint: BlueprintDict }` |

#### ThinkingNode Schema

```typescript
interface ThinkingNode {
  id: string;
  question: string;
  options: Option[];
  allow_custom: boolean;
  parent_id: string | null;
  selected_option_id: string | null;
  custom_input: string | null;
  created_at: string;     // ISO 8601
  position: { x: number; y: number };
  status: 'active' | 'resolved' | 'skipped';
}
```

#### Option Schema

```typescript
interface Option {
  id: string;             // e.g. "A", "B", "C"
  label: string;
  description: string;
  confidence: number;     // 0.0 ~ 1.0
  is_default: boolean;    // True if this is the AI-recommended option
}
```

> **Auto-select Rule**: If an option has `confidence >= 0.85`, the backend will automatically select it without waiting for user input.

### Execution Phase

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `execution.blueprint_loaded` | Execution blueprint generated and ready to render | `{ blueprint: { id: string, steps: ExecutionStep[] } }` |
| `execution.step_started` | A step began execution | `{ step_id: string, name: string, status: 'running', start_time?: string, tool?: string }` |
| `execution.step_completed` | A step finished successfully | `{ step_id: string, name: string, status: 'completed', result?: any, duration_ms: number }` |
| `execution.step_failed` | A step failed | `{ step_id: string, status: 'failed', error: string, can_retry: boolean, error_type?: string, stack_trace?: string }` |
| `execution.intervention_needed` | Step failed and needs human intervention | `{ step_id: string, step_name: string, reason: string, suggested_actions: SuggestedAction[] }` |
| `execution.returned_to_thinking` | Replan triggered, returning to thinking phase | `{ archived_step_ids: string[] }` |
| `execution.replanned` | New blueprint generated after replan | `{ from_step_id: string, abandoned_steps: string[], new_steps: ExecutionStep[] }` |
| `execution.paused` | Execution paused by user or system | `{ blueprint_id: string }` |
| `execution.resumed` | Execution resumed | `{ blueprint_id: string }` |
| `execution.completed` | All steps finished | `{ success: boolean, summary: string, completed_steps: number, total_steps: number, execution_time: number, can_save: boolean }` |

#### ExecutionStep Schema

```typescript
interface ExecutionStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'skipped';
  dependencies: string[];     // Step IDs
  position: { x: number; y: number };
  tool?: string;
  is_main_path: boolean;
  is_convergence: boolean;
  convergence_type?: 'parallel' | 'sequential';
  result?: any;
  error?: string;
  needs_intervention?: boolean;
  is_archived?: boolean;
}
```

#### SuggestedAction Schema

```typescript
interface SuggestedAction {
  id: 'replan' | 'skip' | 'retry' | 'custom';
  label: string;
  description: string;
}
```

### Visual Adapter (Vis-Adapter)

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `vis.preview` | Visual preview with screenshot and analysis | `{ screenshot_id: string, image_base64: string, width: number, height: number, annotations: any[], analysis: { scene_type: string, elements: any[], suggested_next_action: string } }` |
| `vis.action_executed` | Visual action execution result | `{ action: string, result: any }` |

### Freeze / Screenshot / Annotation

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `freeze.confirmed` | Freeze request acknowledged, screenshot attached | `{ adapterId: string, stepId: string, screenshot: string, freezeToken: string }` |
| `screenshot` | Step execution screenshot pushed automatically | `{ adapterId: string, stepId: string, image: string, timestamp: number }` |
| `annotation.submitted` | Annotation saved and execution resumed | `{ step_id: string, annotation: string, boxes: BoxAnnotation[], freeze_token?: string }` |
| `status_update` | Generic status update (resumed, retrying, etc.) | `{ adapterId: string, status: string, step_id: string, message: string, ... }` |

#### BoxAnnotation Schema

```typescript
interface BoxAnnotation {
  id: string;
  x: number;      // top-left x coordinate (natural image pixels)
  y: number;      // top-left y coordinate (natural image pixels)
  w: number;      // width in pixels
  h: number;      // height in pixels
  label?: string; // optional label
}
```

---

## Frontend → Backend Messages

### Task Control

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `task.start` | Start a new task | `{ user_input: string }` |
| `task.interrupt` | Interrupt current task | `{ task_id: string }` |

### Thinking Control

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `thinking.select_option` | Select an A/B/C option | `{ task_id: string, current_node_id: string, option_id: string }` |
| `thinking.custom_input` | Submit custom text input | `{ task_id: string, current_node_id: string, custom_input: string }` |
| `thinking.confirm_execution` | **(Optional in auto-mode)** Manually confirm execution | `{ task_id: string }` |

> **Note**: In auto-convergence mode (v2.5+), the backend automatically generates the execution blueprint when thinking converges. `thinking.confirm_execution` is still accepted for backward compatibility and will reuse the existing blueprint if one was already auto-generated.

### Execution Control

| Type | Description | Payload Schema |
|------|-------------|----------------|
| `execution.start` | Start execution for a blueprint | `{ task_id: string, blueprint_id?: string }` |
| `execution.pause` | Pause execution | `{ task_id: string, blueprint_id: string }` |
| `execution.resume` | Resume execution | `{ task_id: string, blueprint_id: string }` |
| `execution.intervene` | Submit intervention action | `{ task_id: string, blueprint_id: string, step_id: string, action: 'replan' \| 'skip' \| 'retry' \| 'modify', custom_input?: string }` |
| `execution.cancel` | Cancel execution | `{ task_id: string, blueprint_id: string }` |

### Intervention Action Detail

```typescript
interface InterventionPayload {
  task_id: string;
  blueprint_id: string;
  step_id: string;
  action: 'replan' | 'skip' | 'retry' | 'modify';
  custom_input?: string;    // Required when action is 'modify' or 'replan'
}
```

### Visual Adapter Control

| Type | Description | Payload |
|------|-------------|---------|
| `vis.preview` | Request visual preview | `{ task_id: string, target: string }` |
| `vis.user_selection` | User selected an element | `{ element_id: string }` |
| `vis.confirm` | Confirm visual action | `{ action_id: string }` |
| `vis.skip` | Skip visual step | `{ step_id: string }` |
| `vis.batch_confirm` | Batch confirm multiple actions | `{ action_ids: string[] }` |
| `vis.action` | Execute a visual action | `{ action: string, params: any }` |

### Tool System

| Type | Description | Payload |
|------|-------------|---------|
| `tools.list` | List available tools | `{}` |
| `tools.inspect` | Inspect a tool | `{ tool_id: string }` |
| `node.bind_tool` | Bind tool to a node | `{ node_id: string, tool_id: string }` |
| `node.unlock_tool` | Unlock a tool binding | `{ node_id: string }` |

### MCP & Sandbox

| Type | Description | Payload |
|------|-------------|---------|
| `mcp.execute` | Execute MCP command | `{ command: string, args: any[] }` |
| `mcp.refresh` | Refresh MCP state | `{}` |
| `sandbox.execute` | Execute in sandbox | `{ code: string, language: string }` |
| `sandbox.create` | Create sandbox | `{ config: any }` |
| `sandbox.cleanup` | Cleanup sandbox | `{ sandbox_id: string }` |

### Adapter Studio (CRUD)

| Type | Description | Payload |
|------|-------------|---------|
| `adapter.list` | List adapters | `{ filter?: string }` |
| `adapter.get` | Get adapter detail | `{ adapter_id: string }` |
| `adapter.create` | Create adapter | `{ name: string, type: string, config: any }` |
| `adapter.update` | Update adapter | `{ adapter_id: string, config: any }` |
| `adapter.delete` | Delete adapter | `{ adapter_id: string }` |
| `adapter.clone` | Clone adapter | `{ adapter_id: string }` |
| `adapter.add_input` | Add input to adapter | `{ adapter_id: string, input: any }` |
| `adapter.attach_to_step` | Attach adapter to step | `{ adapter_id: string, step_id: string }` |
| `adapter.detach_from_step` | Detach adapter from step | `{ adapter_id: string, step_id: string }` |
| `adapter.enter_edit` | Enter edit mode | `{ adapter_id: string }` |
| `adapter.execute` | Execute adapter | `{ adapter_id: string, params: any }` |

### Adapter Runtime Control

| Type | Description | Payload |
|------|-------------|---------|
| `adapter.blueprint.attach` | Attach adapter to blueprint | `{ adapter_id: string, blueprint_id: string }` |
| `adapter.blueprint.detach` | Detach adapter from blueprint | `{ adapter_id: string, blueprint_id: string }` |
| `adapter.runtime.start` | Start adapter runtime | `{ blueprint_id: string }` |
| `adapter.runtime.pause` | Pause adapter runtime | `{ blueprint_id: string }` |
| `adapter.runtime.resume` | Resume adapter runtime | `{ blueprint_id: string }` |
| `adapter.runtime.freeze` | Freeze execution | `{ blueprint_id: string, step_id: string }` |
| `adapter.runtime.unfreeze` | Unfreeze execution | `{ blueprint_id: string, step_id: string }` |
| `adapter.runtime.retry` | Retry failed step | `{ blueprint_id: string, step_id: string }` |
| `adapter.runtime.replan` | Replan from step | `{ blueprint_id: string, step_id: string, context?: string }` |
| `adapter.runtime.dismiss_annotation` | Dismiss freeze annotation | `{ blueprint_id: string, step_id: string }` |

### Freeze / Annotation Control (V2.5 Frontend API)

| Type | Description | Payload |
|------|-------------|---------|
| `freeze_request` | Request freeze on current step + capture screenshot | `{ task_id: string, step_id: string, reason?: string }` |
| `submit_annotation` | Submit annotation boxes + text and resume | `{ task_id: string, step_id: string, annotation?: string, boxes?: BoxAnnotation[], freeze_token?: string }` |
| `retry_step` | Retry current failed step | `{ task_id: string, step_id: string, reason?: string }` |
| `request_replan` | Request replan from current step | `{ task_id: string, step_id: string, context?: string }` |
| `confirm_replan` | Accept or reject replanned blueprint | `{ task_id: string, step_id: string, action: 'accept' \| 'reject' }` |

> **Note**: `freeze_request` → `freeze.confirmed` (screenshot) → `submit_annotation` (boxes) → `annotation.submitted` is the full freeze-annotation round-trip.

---

## State Transition Diagram

```
[input] --task.start--> [thinking]
                            |
                            | thinking.node_created/selected
                            v
                    [option selection]
                            |
                            | (3 layers OR auto-select confidence>=0.85)
                            v
                    [thinking.converged]
                            |
                            | _auto_generate_blueprint()
                            v
                    [execution.blueprint_loaded]
                            |
                            | execution.step_started/completed
                            v
                    [execution.completed]
                            |
                            | OR execution.intervention_needed
                            v
                    [intervention panel]
                            |
                            | action: replan
                            v
                    [execution.returned_to_thinking]
```

---

## Change Log

### v2.5+ (2026-04-24) — Freeze / Annotation / Screenshot

- **Added** `freeze.confirmed` message — backend pushes screenshot when freeze is requested
- **Added** `screenshot` message — automatically pushed after each Web step execution
- **Added** `submit_annotation` V2 API — accepts `boxes` array with `{x, y, w, h, label}`
- **Added** `annotation.submitted` response — returns saved boxes with generated annotation IDs
- **Added** `FreezeOverlay` frontend component — screenshot display + box drawing + text annotation
- **Added** `ExecutionNode` freeze button — click to trigger `freeze_request` on running steps
- **Fixed** `adapter_runtime_manager` auto-attach — `freeze_request` and `submit_annotation` create runtime if missing

### v2.5 (2026-04-04)

- **Added** `thinking.converged` event for auto-transition from thinking to execution
- **Added** `_auto_generate_blueprint()` in `message_router` — converges thinking and immediately generates execution blueprint without requiring manual `thinking.confirm_execution`
- **Added** `AUTO_SELECT_THRESHOLD = 0.85` in `thinking_engine` — high-confidence options are automatically selected
- **Modified** `_handle_thinking_confirm_execution` to reuse existing blueprint if already auto-generated
