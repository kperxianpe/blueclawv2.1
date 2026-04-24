# -*- coding: utf-8 -*-
"""
RecoveryController - 故障恢复控制器

决策树：
1. 自动重试（同参数）
2. 备用选择器重试
3. 回滚到最近检查点
4. 暂停（等待干预）
"""
import copy
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from blueclaw.adapter.models import ExecutionStep, TargetDescription
from blueclaw.adapter.web.checkpoint import WebCheckpointManager


class RecoveryConfig(BaseModel):
    """恢复策略配置"""
    max_retries: int = 2
    retry_backoff_ms: int = 500
    fallback_selectors: List[str] = Field(default_factory=list)
    enable_rollback: bool = True
    pause_on_failure: bool = False


class RecoveryAction(BaseModel):
    """恢复动作结果"""
    action: str = ""  # retry / fallback / rollback / pause / abort
    params: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class RecoveryController:
    """故障恢复控制器"""

    def __init__(
        self,
        web_checkpoint_manager: WebCheckpointManager,
        config: Optional[RecoveryConfig] = None,
    ):
        self.web_checkpoint_manager = web_checkpoint_manager
        self.config = config or RecoveryConfig()

    async def recover(
        self,
        page,
        failed_step: ExecutionStep,
        failure_error: str,
        blueprint_id: str,
        executor,
    ) -> RecoveryAction:
        """
        执行恢复策略决策树。
        executor 为 WebExecutor 实例，用于重试步骤。
        """
        # 1. 自动重试
        if self.config.max_retries > 0:
            for attempt in range(1, self.config.max_retries + 1):
                await page.wait_for_timeout(self.config.retry_backoff_ms)
                result = await executor.execute_step(
                    failed_step, page, blueprint_id=blueprint_id, _skip_recovery=True
                )
                if result.status == "success":
                    return RecoveryAction(
                        action="retry",
                        message=f"Retry succeeded on attempt {attempt}",
                        params={"attempt": attempt},
                    )

        # 2. 备用选择器重试
        for fb_selector in self.config.fallback_selectors:
            mutated_step = copy.deepcopy(failed_step)
            mutated_step.action.target = TargetDescription(selector=fb_selector)
            result = await executor.execute_step(
                mutated_step, page, blueprint_id=blueprint_id, _skip_recovery=True
            )
            if result.status == "success":
                return RecoveryAction(
                    action="fallback",
                    message=f"Fallback selector succeeded: {fb_selector}",
                    params={"fallback_selector": fb_selector},
                )

        # 3. 回滚到最近检查点
        if self.config.enable_rollback:
            cps = self.web_checkpoint_manager.list_checkpoints(blueprint_id)
            if cps:
                latest_cp_id = cps[-1]["checkpoint_id"]
                restored = await self.web_checkpoint_manager.restore(
                    page, blueprint_id, latest_cp_id
                )
                if restored:
                    return RecoveryAction(
                        action="rollback",
                        message=f"Rolled back to checkpoint {latest_cp_id}",
                        params={
                            "checkpoint_id": latest_cp_id,
                            "step_id": restored.step_id,
                        },
                    )

        # 4. 暂停（等待用户干预）
        return RecoveryAction(
            action="pause",
            message="All recovery strategies exhausted",
            params={"failure_error": failure_error},
        )
