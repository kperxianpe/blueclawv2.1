# -*- coding: utf-8 -*-
"""
AdapterManager

- 蓝图路由（web / ide）
- 生命周期管理（init / execute / pause / resume / cleanup）
- 与 Core 层的通信接口（同进程直接调用）
"""
from typing import Dict, Optional
from blueclaw.adapter.adapters.base import BaseAdapter
from blueclaw.adapter.adapters.web import WebAdapter
from blueclaw.adapter.adapters.ide import IDEAdapter
from blueclaw.adapter.models import ExecutionBlueprint, ExecutionResult
from blueclaw.adapter.state import StateMachine, AdapterState, FileStatePersistence, EventBus
from blueclaw.adapter.exceptions import AdapterException, ExecutionAdapterException, ValidationAdapterException


class AdapterManager:
    """适配器管理器"""

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {
            "web": WebAdapter(),
            "ide": IDEAdapter(),
        }
        self._state_machines: Dict[str, StateMachine] = {}
        self._task_adapter_map: Dict[str, str] = {}  # task_id -> adapter_type
        self._persistence = FileStatePersistence()
        self._event_bus = EventBus()

    def get_adapter(self, adapter_type: str) -> BaseAdapter:
        if adapter_type not in self._adapters:
            raise ValueError(f"Unsupported adapter type: {adapter_type}")
        return self._adapters[adapter_type]

    def _get_or_create_state_machine(self, task_id: str) -> StateMachine:
        if task_id not in self._state_machines:
            self._state_machines[task_id] = StateMachine(
                task_id=task_id,
                persistence=self._persistence,
                event_bus=self._event_bus,
            )
        return self._state_machines[task_id]

    async def execute(self, blueprint: ExecutionBlueprint) -> ExecutionResult:
        task_id = blueprint.task_id
        adapter_type = blueprint.adapter_type
        self._task_adapter_map[task_id] = adapter_type
        adapter = self.get_adapter(adapter_type)
        sm = self._get_or_create_state_machine(task_id)

        try:
            await sm.transition(AdapterState.PLANNING, {"action": "init"})
            await adapter.init(blueprint)

            await sm.transition(AdapterState.EXECUTING, {"action": "execute"})
            result = await adapter.execute(blueprint)

            # 若存在验证规则，进入 VALIDATING
            has_validation = any(step.validation for step in blueprint.steps)
            if has_validation:
                await sm.transition(AdapterState.VALIDATING, {"action": "validate"})
                # 最小实现：模拟验证通过
                # 未来在此处接入真实验证逻辑

            if result.success:
                await sm.transition(AdapterState.COMPLETED, {"action": "finish"})
            else:
                await sm.transition(AdapterState.FAILED, {"action": "execution_failed"})
                raise ExecutionAdapterException(
                    "Adapter execution returned failure",
                    context={"blueprint_id": task_id, "adapter_type": blueprint.adapter_type},
                )

            return result
        except AdapterException:
            await sm.transition(AdapterState.FAILED, {"action": "error"})
            raise
        except Exception as e:
            await sm.transition(AdapterState.FAILED, {"action": "unexpected_error"})
            raise ExecutionAdapterException(
                str(e),
                context={"blueprint_id": task_id, "adapter_type": blueprint.adapter_type},
            ) from e

    async def pause(self, task_id: str) -> None:
        sm = self._get_or_create_state_machine(task_id)
        if sm.current not in (AdapterState.EXECUTING, AdapterState.PLANNING, AdapterState.VALIDATING):
            raise ValueError(f"Cannot pause from state {sm.current.value}")
        adapter = self._adapters.get(self._guess_adapter_type(task_id))
        if adapter:
            await adapter.pause()
        await sm.transition(AdapterState.PAUSED, {"action": "pause"})

    async def resume(self, task_id: str) -> None:
        sm = self._get_or_create_state_machine(task_id)
        if sm.current != AdapterState.PAUSED:
            raise ValueError(f"Cannot resume from state {sm.current.value}")
        adapter = self._adapters.get(self._guess_adapter_type(task_id))
        if adapter:
            await adapter.resume()
        # 恢复后回到 EXECUTING（简化处理）
        await sm.transition(AdapterState.EXECUTING, {"action": "resume"})

    async def cancel(self, task_id: str) -> None:
        sm = self._get_or_create_state_machine(task_id)
        adapter = self._adapters.get(self._guess_adapter_type(task_id))
        if adapter:
            await adapter.cleanup()
        await sm.transition(AdapterState.FAILED, {"action": "cancel"})

    def _guess_adapter_type(self, task_id: str) -> Optional[str]:
        return self._task_adapter_map.get(task_id)
    
    async def screenshot(self, task_id: str) -> str:
        """获取指定任务的当前截图（Base64）"""
        adapter_type = self._task_adapter_map.get(task_id)
        if not adapter_type:
            return ""
        adapter = self._adapters.get(adapter_type)
        if not adapter:
            return ""
        raw = await adapter._capture_screenshot()
        if not raw:
            return ""
        import base64
        return base64.b64encode(raw).decode("utf-8")

    @staticmethod
    def from_core_blueprint(core_blueprint: Dict) -> ExecutionBlueprint:
        """将 Core 层 dataclass/dict 转换为 Adapter 层 Pydantic 模型"""
        steps = []
        for s in core_blueprint.get("steps", []):
            action = s.get("action", {})
            target = action.get("target", {})
            validation = s.get("validation")
            steps.append({
                "step_id": s.get("step_id", s.get("id", "")),
                "name": s.get("name", ""),
                "action": {
                    "type": action.get("type", "navigate"),
                    "target": {
                        "semantic": target.get("semantic", ""),
                        "selector": target.get("selector"),
                        "coordinates": target.get("coordinates"),
                    } if target else None,
                    "params": action.get("params", {}),
                },
                "dependencies": s.get("dependencies", []),
                "validation": {
                    "type": validation.get("type", "presence"),
                    "expected": validation.get("expected"),
                } if validation else None,
            })
        return ExecutionBlueprint(
            task_id=core_blueprint.get("task_id", core_blueprint.get("id", "")),
            adapter_type=core_blueprint.get("adapter_type", "web"),
            steps=steps,
            config=core_blueprint.get("config", {}),
        )
