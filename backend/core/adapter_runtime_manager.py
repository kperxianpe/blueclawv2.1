#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter Runtime Manager
Manages the runtime state of Adapter Studios (visual workspaces).

Concept: Adapter = Agent's visual studio.
- One ExecutionBlueprint binds to exactly one Adapter Studio during execution.
- One Adapter Studio can serve multiple blueprints serially.
- All runtime states (running/paused/frozen/error), annotations, and URLs/files
  are tracked here and pushed to connected clients via WebSocket.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any
from copy import deepcopy


@dataclass
class Annotation:
    id: str
    level: Literal["info", "warning", "error", "freeze"]
    message: str
    rect: Optional[Dict[str, int]] = None
    timestamp: int = 0
    step_id: Optional[str] = None


@dataclass
class RuntimeState:
    """Runtime snapshot of an Adapter Studio bound to a blueprint."""
    studio_id: str
    blueprint_id: str
    task_id: str
    adapter_type: Literal["web", "ide", "canvas", "default"] = "default"
    state: Literal["idle", "connecting", "running", "paused", "error", "frozen"] = "idle"
    current_url: Optional[str] = None
    current_file: Optional[str] = None
    annotations: List[Annotation] = field(default_factory=list)
    last_updated: int = 0

    def to_dict(self) -> dict:
        return {
            "studio_id": self.studio_id,
            "blueprint_id": self.blueprint_id,
            "task_id": self.task_id,
            "adapter_type": self.adapter_type,
            "state": self.state,
            "current_url": self.current_url,
            "current_file": self.current_file,
            "annotations": [
                {
                    "id": a.id,
                    "level": a.level,
                    "message": a.message,
                    "rect": a.rect,
                    "timestamp": a.timestamp,
                    "step_id": a.step_id,
                }
                for a in self.annotations
            ],
            "last_updated": self.last_updated,
        }


class AdapterRuntimeManager:
    """
    Singleton manager for all adapter runtime states.
    Keyed by blueprint_id (since one blueprint maps to one studio at a time).
    """

    def __init__(self):
        # Key: blueprint_id → RuntimeState
        self._runtimes: Dict[str, RuntimeState] = {}
        # Key: studio_id → currently bound blueprint_id (for serial reuse tracking)
        self._studio_bindings: Dict[str, Optional[str]] = {}
        self._websocket_server = None

    def set_websocket_server(self, server):
        self._websocket_server = server

    # ── Binding Lifecycle ─────────────────────────────────────────

    def attach(self, blueprint_id: str, task_id: str, studio_id: str, adapter_type: str = "default") -> RuntimeState:
        """Bind a blueprint to a studio."""
        runtime = RuntimeState(
            studio_id=studio_id,
            blueprint_id=blueprint_id,
            task_id=task_id,
            adapter_type=adapter_type,  # type: ignore[arg-type]
            state="idle",
            last_updated=int(time.time() * 1000),
        )
        self._runtimes[blueprint_id] = runtime
        self._studio_bindings[studio_id] = blueprint_id
        return deepcopy(runtime)

    def detach(self, blueprint_id: str) -> Optional[RuntimeState]:
        """Unbind a blueprint from its studio."""
        runtime = self._runtimes.pop(blueprint_id, None)
        if runtime:
            self._studio_bindings[runtime.studio_id] = None
        return deepcopy(runtime) if runtime else None

    def get(self, blueprint_id: str) -> Optional[RuntimeState]:
        return deepcopy(self._runtimes.get(blueprint_id))

    # ── State Transitions ─────────────────────────────────────────

    def set_state(self, blueprint_id: str, state: str) -> Optional[RuntimeState]:
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return None
        runtime.state = state  # type: ignore[assignment]
        runtime.last_updated = int(time.time() * 1000)
        return deepcopy(runtime)

    def set_url(self, blueprint_id: str, url: str) -> Optional[RuntimeState]:
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return None
        runtime.current_url = url
        runtime.last_updated = int(time.time() * 1000)
        return deepcopy(runtime)

    def set_file(self, blueprint_id: str, file_path: str) -> Optional[RuntimeState]:
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return None
        runtime.current_file = file_path
        runtime.last_updated = int(time.time() * 1000)
        return deepcopy(runtime)

    # ── Annotations ───────────────────────────────────────────────

    def add_annotation(self, blueprint_id: str, level: str, message: str, rect: Optional[dict] = None, step_id: Optional[str] = None) -> Optional[Annotation]:
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return None
        ann = Annotation(
            id=f"ann_{uuid.uuid4().hex[:8]}",
            level=level,  # type: ignore[arg-type]
            message=message,
            rect=rect,
            timestamp=int(time.time() * 1000),
            step_id=step_id,
        )
        runtime.annotations.append(ann)
        runtime.last_updated = ann.timestamp
        return deepcopy(ann)

    def remove_annotation(self, blueprint_id: str, annotation_id: str) -> bool:
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return False
        original_len = len(runtime.annotations)
        runtime.annotations = [a for a in runtime.annotations if a.id != annotation_id]
        return len(runtime.annotations) < original_len

    def clear_annotations(self, blueprint_id: str) -> bool:
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return False
        runtime.annotations.clear()
        runtime.last_updated = int(time.time() * 1000)
        return True

    # ── WebSocket Push Helpers ────────────────────────────────────

    async def _push(self, blueprint_id: str, msg_type: str, payload: dict):
        if not self._websocket_server:
            return
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return
        from blueclaw.api.messages import Message
        msg = Message.create(msg_type, payload, task_id=runtime.task_id)
        await self._websocket_server.broadcast_to_task(runtime.task_id, msg)

    async def push_state(self, blueprint_id: str):
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return
        await self._push(blueprint_id, "adapter.runtime.state", runtime.to_dict())

    async def push_annotated(self, blueprint_id: str, annotation: Annotation):
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return
        await self._push(
            blueprint_id,
            "adapter.runtime.annotated",
            {
                "blueprint_id": blueprint_id,
                "studio_id": runtime.studio_id,
                "annotation": {
                    "id": annotation.id,
                    "level": annotation.level,
                    "message": annotation.message,
                    "rect": annotation.rect,
                    "timestamp": annotation.timestamp,
                    "step_id": annotation.step_id,
                },
            },
        )

    async def push_frozen(self, blueprint_id: str, reason: str = ""):
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return
        await self._push(
            blueprint_id,
            "adapter.runtime.frozen",
            {
                "blueprint_id": blueprint_id,
                "studio_id": runtime.studio_id,
                "reason": reason,
                "timestamp": int(time.time() * 1000),
            },
        )

    async def push_unfrozen(self, blueprint_id: str):
        runtime = self._runtimes.get(blueprint_id)
        if not runtime:
            return
        await self._push(
            blueprint_id,
            "adapter.runtime.unfrozen",
            {
                "blueprint_id": blueprint_id,
                "studio_id": runtime.studio_id,
                "timestamp": int(time.time() * 1000),
            },
        )


# Global singleton
adapter_runtime_manager = AdapterRuntimeManager()
