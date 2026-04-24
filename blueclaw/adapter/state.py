# -*- coding: utf-8 -*-
"""
Adapter 状态管理机制

- 执行状态机（idle/planning/executing/validating/paused/completed/failed）
- 状态变更事件发布/订阅
- 状态持久化（文件）
- 并发安全控制（asyncio.Lock）
"""
import os
import json
import asyncio
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, List, Callable, Optional


class AdapterState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# 合法状态转换矩阵
_VALID_TRANSITIONS: Dict[AdapterState, List[AdapterState]] = {
    AdapterState.IDLE: [AdapterState.PLANNING],
    AdapterState.PLANNING: [AdapterState.EXECUTING, AdapterState.PAUSED, AdapterState.FAILED],
    AdapterState.EXECUTING: [AdapterState.VALIDATING, AdapterState.PAUSED, AdapterState.COMPLETED, AdapterState.FAILED],
    AdapterState.VALIDATING: [AdapterState.COMPLETED, AdapterState.EXECUTING, AdapterState.FAILED],
    AdapterState.PAUSED: [AdapterState.EXECUTING, AdapterState.FAILED],
    AdapterState.COMPLETED: [AdapterState.IDLE],
    AdapterState.FAILED: [AdapterState.IDLE],
}


class EventBus:
    """异步事件总线"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        callbacks = self._subscribers.get(event_type, [])
        if not callbacks:
            return
        await asyncio.gather(
            *[cb(payload) for cb in callbacks],
            return_exceptions=True
        )


class FileStatePersistence:
    """文件状态持久化"""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "sessions", "adapter_state"
            )
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, task_id: str) -> str:
        return os.path.join(self.base_dir, f"{task_id}.json")

    def save(self, task_id: str, state: AdapterState, history: List[Dict[str, Any]]) -> None:
        record = {
            "task_id": task_id,
            "state": state.value,
            "history": history,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._path(task_id), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(task_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


class StateMachine:
    """Adapter 执行状态机"""

    def __init__(
        self,
        task_id: str,
        persistence: Optional[FileStatePersistence] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.task_id = task_id
        self._current = AdapterState.IDLE
        self._lock = asyncio.Lock()
        self._history: List[Dict[str, Any]] = []
        self._persistence = persistence or FileStatePersistence()
        self._event_bus = event_bus or EventBus()

    @property
    def current(self) -> AdapterState:
        return self._current

    async def transition(self, to_state: AdapterState, meta: Optional[Dict[str, Any]] = None) -> None:
        async with self._lock:
            if to_state not in _VALID_TRANSITIONS.get(self._current, []) and to_state != AdapterState.FAILED:
                # FAILED 允许从任意状态兜底进入
                if to_state == AdapterState.FAILED:
                    pass
                else:
                    raise ValueError(
                        f"Invalid state transition: {self._current.value} -> {to_state.value}"
                    )

            from_state = self._current
            self._current = to_state
            entry = {
                "from": from_state.value,
                "to": to_state.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "meta": meta or {},
            }
            self._history.append(entry)
            self._persistence.save(self.task_id, self._current, self._history)
            await self._event_bus.publish(
                "state.changed",
                {
                    "task_id": self.task_id,
                    "from": from_state.value,
                    "to": to_state.value,
                    "meta": meta or {},
                },
            )

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    # 便捷状态转换方法（与验收测试伪代码对齐）
    async def start_execution(self, meta: Optional[Dict[str, Any]] = None) -> None:
        if self._current == AdapterState.IDLE:
            await self.transition(AdapterState.PLANNING, {"auto": True, **(meta or {})})
        await self.transition(AdapterState.EXECUTING, meta)

    async def pause(self, meta: Optional[Dict[str, Any]] = None) -> None:
        await self.transition(AdapterState.PAUSED, meta)

    async def resume(self, meta: Optional[Dict[str, Any]] = None) -> None:
        await self.transition(AdapterState.EXECUTING, meta)

    async def complete(self, meta: Optional[Dict[str, Any]] = None) -> None:
        if self._current == AdapterState.EXECUTING:
            # 自动跳过 VALIDATING（如果无需验证）
            pass
        await self.transition(AdapterState.COMPLETED, meta)

    async def fail(self, meta: Optional[Dict[str, Any]] = None) -> None:
        await self.transition(AdapterState.FAILED, meta)
