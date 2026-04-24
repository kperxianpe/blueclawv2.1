#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter Runtime Handlers — v2.5 Unified Protocol
Handles studio binding, runtime control, and state transitions.
"""
from backend.core.adapter_runtime_manager import adapter_runtime_manager
from blueclaw.api.messages import Message


# ── Blueprint Binding ───────────────────────────────────────────

async def handle_adapter_blueprint_attach(websocket, payload: dict, server) -> dict:
    """adapter.blueprint.attach — Bind an ExecutionBlueprint to a Studio."""
    task_id = payload.get("task_id")
    blueprint_id = payload.get("blueprint_id")
    studio_id = payload.get("studio_id")
    adapter_type = payload.get("adapter_type", "default")

    if not all([task_id, blueprint_id, studio_id]):
        return Message.create("error", {"message": "Missing task_id, blueprint_id, or studio_id"}, task_id=task_id)

    runtime = adapter_runtime_manager.attach(blueprint_id, task_id, studio_id, adapter_type)

    # Broadcast to all clients on this task
    await server.broadcast_to_task(
        task_id,
        Message.create(
            "adapter.blueprint.attached",
            {
                "task_id": task_id,
                "blueprint_id": blueprint_id,
                "studio_id": studio_id,
                "adapter_type": adapter_type,
                "state": runtime.state,
            },
            task_id=task_id,
        ),
    )

    return Message.create(
        "adapter.blueprint.attach_success",
        {"blueprint_id": blueprint_id, "studio_id": studio_id, "state": runtime.state},
        task_id=task_id,
    )


async def handle_adapter_blueprint_detach(websocket, payload: dict, server) -> dict:
    """adapter.blueprint.detach — Unbind a blueprint from its studio."""
    task_id = payload.get("task_id")
    blueprint_id = payload.get("blueprint_id")

    if not blueprint_id:
        return Message.create("error", {"message": "Missing blueprint_id"}, task_id=task_id)

    runtime = adapter_runtime_manager.detach(blueprint_id)
    studio_id = runtime.studio_id if runtime else None

    await server.broadcast_to_task(
        task_id,
        Message.create(
            "adapter.blueprint.detached",
            {"blueprint_id": blueprint_id, "studio_id": studio_id},
            task_id=task_id,
        ),
    )

    return Message.create(
        "adapter.blueprint.detach_success",
        {"blueprint_id": blueprint_id, "studio_id": studio_id},
        task_id=task_id,
    )


# ── Runtime Control ─────────────────────────────────────────────

async def _transition_state(blueprint_id: str, new_state: str, server) -> dict:
    """Helper: transition runtime state and broadcast."""
    runtime = adapter_runtime_manager.set_state(blueprint_id, new_state)
    if not runtime:
        return Message.create("error", {"message": f"Runtime not found for blueprint: {blueprint_id}"})

    await adapter_runtime_manager.push_state(blueprint_id)
    return Message.create(
        "adapter.runtime.state",
        runtime.to_dict(),
        task_id=runtime.task_id,
    )


async def handle_adapter_runtime_start(websocket, payload: dict, server) -> dict:
    """adapter.runtime.start — Start the studio running."""
    blueprint_id = payload.get("blueprint_id")
    return await _transition_state(blueprint_id, "running", server)


async def handle_adapter_runtime_pause(websocket, payload: dict, server) -> dict:
    """adapter.runtime.pause — Pause execution."""
    blueprint_id = payload.get("blueprint_id")
    return await _transition_state(blueprint_id, "paused", server)


async def handle_adapter_runtime_resume(websocket, payload: dict, server) -> dict:
    """adapter.runtime.resume — Resume execution."""
    blueprint_id = payload.get("blueprint_id")
    return await _transition_state(blueprint_id, "running", server)


async def handle_adapter_runtime_freeze(websocket, payload: dict, server) -> dict:
    """adapter.runtime.freeze — Freeze studio (user intervention)."""
    blueprint_id = payload.get("blueprint_id")
    reason = payload.get("reason", "")
    runtime = adapter_runtime_manager.set_state(blueprint_id, "frozen")
    if not runtime:
        return Message.create("error", {"message": f"Runtime not found for blueprint: {blueprint_id}"})

    await adapter_runtime_manager.push_frozen(blueprint_id, reason)
    await adapter_runtime_manager.push_state(blueprint_id)
    return Message.create(
        "adapter.runtime.state",
        runtime.to_dict(),
        task_id=runtime.task_id,
    )


async def handle_adapter_runtime_unfreeze(websocket, payload: dict, server) -> dict:
    """adapter.runtime.unfreeze — Unfreeze studio."""
    blueprint_id = payload.get("blueprint_id")
    runtime = adapter_runtime_manager.set_state(blueprint_id, "running")
    if not runtime:
        return Message.create("error", {"message": f"Runtime not found for blueprint: {blueprint_id}"})

    await adapter_runtime_manager.push_unfrozen(blueprint_id)
    await adapter_runtime_manager.push_state(blueprint_id)
    return Message.create(
        "adapter.runtime.state",
        runtime.to_dict(),
        task_id=runtime.task_id,
    )


async def handle_adapter_runtime_retry(websocket, payload: dict, server) -> dict:
    """adapter.runtime.retry — Retry current step."""
    blueprint_id = payload.get("blueprint_id")
    reason = payload.get("reason", "")
    runtime = adapter_runtime_manager.get(blueprint_id)
    if not runtime:
        return Message.create("error", {"message": f"Runtime not found for blueprint: {blueprint_id}"})

    # Add a freeze-level annotation as retry marker
    adapter_runtime_manager.add_annotation(
        blueprint_id, "freeze", f"Retry requested: {reason}", step_id=payload.get("step_id")
    )
    await adapter_runtime_manager.push_state(blueprint_id)
    return Message.create(
        "adapter.runtime.retry_ack",
        {"blueprint_id": blueprint_id, "reason": reason},
        task_id=runtime.task_id,
    )


async def handle_adapter_runtime_replan(websocket, payload: dict, server) -> dict:
    """adapter.runtime.replan — Replan from current step."""
    blueprint_id = payload.get("blueprint_id")
    reason = payload.get("reason", "")
    runtime = adapter_runtime_manager.get(blueprint_id)
    if not runtime:
        return Message.create("error", {"message": f"Runtime not found for blueprint: {blueprint_id}"})

    adapter_runtime_manager.add_annotation(
        blueprint_id, "warning", f"Replan requested: {reason}", step_id=payload.get("step_id")
    )
    await adapter_runtime_manager.push_state(blueprint_id)
    return Message.create(
        "adapter.runtime.replan_ack",
        {"blueprint_id": blueprint_id, "reason": reason},
        task_id=runtime.task_id,
    )


async def handle_adapter_runtime_dismiss_annotation(websocket, payload: dict, server) -> dict:
    """adapter.runtime.dismiss_annotation — Client dismissed an annotation."""
    blueprint_id = payload.get("blueprint_id")
    annotation_id = payload.get("annotation_id")
    ok = adapter_runtime_manager.remove_annotation(blueprint_id, annotation_id)
    runtime = adapter_runtime_manager.get(blueprint_id)
    return Message.create(
        "adapter.runtime.annotation_dismissed",
        {"blueprint_id": blueprint_id, "annotation_id": annotation_id, "success": ok},
        task_id=runtime.task_id if runtime else None,
    )


# ── Internal Helpers (called by execution_engine, not from client) ──

async def notify_step_started(blueprint_id: str, step_id: str, step_name: str):
    """Called by execution_engine when a step starts."""
    runtime = adapter_runtime_manager.set_state(blueprint_id, "running")
    if runtime:
        await adapter_runtime_manager.push_state(blueprint_id)


async def notify_step_completed(blueprint_id: str, step_id: str, result: dict):
    """Called by execution_engine when a step completes."""
    runtime = adapter_runtime_manager.get(blueprint_id)
    if runtime:
        await adapter_runtime_manager.push_state(blueprint_id)


async def notify_step_failed(blueprint_id: str, step_id: str, error: str):
    """Called by execution_engine when a step fails."""
    runtime = adapter_runtime_manager.set_state(blueprint_id, "error")
    if runtime:
        adapter_runtime_manager.add_annotation(blueprint_id, "error", error, step_id=step_id)
        await adapter_runtime_manager.push_state(blueprint_id)


async def notify_blueprint_completed(blueprint_id: str):
    """Called by execution_engine when entire blueprint completes."""
    runtime = adapter_runtime_manager.set_state(blueprint_id, "idle")
    if runtime:
        await adapter_runtime_manager.push_state(blueprint_id)
