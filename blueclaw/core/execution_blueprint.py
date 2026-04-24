# -*- coding: utf-8 -*-
"""
execution_blueprint.py - Blueclaw v1.0 执行蓝图系统

基于思考蓝图的输出，构建可视化、可干预的执行流程。
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    PAUSED = "paused"        # 已暂停
    SKIPPED = "skipped"      # 已跳过
    ABORTED = "aborted"      # 已中止


@dataclass
class ExecutionStep:
    """执行步骤"""
    id: str
    name: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    error: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_duration_ms(self) -> float:
        """获取执行时长（毫秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    summary: str
    completed_steps: int
    total_steps: int
    failed_steps: int
    execution_time: float  # seconds
    step_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class InterventionRequest:
    """干预请求"""
    step_id: str
    step_name: str
    reason: str
    suggested_actions: List[str] = field(default_factory=list)


class ExecutionBlueprintSystem:
    """
    执行蓝图系统
    
    管理执行流程，支持可视化、暂停、干预、REPLAN
    """
    
    def __init__(self):
        self.blueprint: Optional[List[ExecutionStep]] = None
        self.current_step_index: int = -1
        self.is_executing: bool = False
        self.is_paused: bool = False
        self.execution_start_time: Optional[datetime] = None
        self.execution_end_time: Optional[datetime] = None
        
        # 回调函数
        self.on_blueprint_loaded: Optional[Callable[[List[ExecutionStep]], None]] = None
        self.on_step_start: Optional[Callable[[ExecutionStep], None]] = None
        self.on_step_complete: Optional[Callable[[ExecutionStep, bool], None]] = None
        self.on_execution_complete: Optional[Callable[[ExecutionResult], None]] = None
        self.on_intervention_needed: Optional[Callable[[InterventionRequest], None]] = None
        
        # 执行历史（用于REPLAN）
        self.completed_steps_history: List[ExecutionStep] = []
        self.abandoned_steps: List[ExecutionStep] = []
    
    def load_blueprint(self, steps_data: List[Dict[str, Any]]) -> List[ExecutionStep]:
        """
        加载执行蓝图
        
        Args:
            steps_data: 步骤数据列表
                [{"name": "步骤名", "description": "描述", ...}]
        """
        self.blueprint = []
        for i, data in enumerate(steps_data):
            step = ExecutionStep(
                id=data.get("id", f"step_{i}"),
                name=data["name"],
                description=data.get("description", ""),
                dependencies=data.get("dependencies", []),
                metadata=data.get("metadata", {})
            )
            self.blueprint.append(step)
        
        self.current_step_index = -1
        
        if self.on_blueprint_loaded:
            self.on_blueprint_loaded(self.blueprint)
        
        return self.blueprint
    
    async def execute_all(self) -> ExecutionResult:
        """执行所有步骤"""
        if not self.blueprint:
            return ExecutionResult(
                success=False,
                summary="No blueprint loaded",
                completed_steps=0,
                total_steps=0,
                failed_steps=0,
                execution_time=0.0
            )
        
        self.is_executing = True
        self.is_paused = False
        self.execution_start_time = datetime.now()
        
        completed = 0
        failed = 0
        
        for i, step in enumerate(self.blueprint):
            if self.is_paused:
                break
            
            self.current_step_index = i
            
            # 检查依赖
            if not self._check_dependencies(step):
                step.status = StepStatus.PENDING
                continue
            
            # 执行步骤
            success = await self._execute_step(step)
            
            if success:
                completed += 1
                self.completed_steps_history.append(step)
            else:
                failed += 1
                # 检查是否需要干预
                if step.status == StepStatus.FAILED:
                    intervention = InterventionRequest(
                        step_id=step.id,
                        step_name=step.name,
                        reason=step.error or "Execution failed"
                    )
                    if self.on_intervention_needed:
                        self.on_intervention_needed(intervention)
                    break
        
        self.is_executing = False
        self.execution_end_time = datetime.now()
        
        execution_time = 0.0
        if self.execution_start_time and self.execution_end_time:
            execution_time = (self.execution_end_time - self.execution_start_time).total_seconds()
        
        result = ExecutionResult(
            success=failed == 0,
            summary=f"Completed {completed}/{len(self.blueprint)} steps",
            completed_steps=completed,
            total_steps=len(self.blueprint),
            failed_steps=failed,
            execution_time=execution_time,
            step_results=[
                {
                    "id": step.id,
                    "name": step.name,
                    "status": step.status.value,
                    "result": step.result,
                    "error": step.error
                }
                for step in self.blueprint
            ]
        )
        
        if self.on_execution_complete:
            self.on_execution_complete(result)
        
        return result
    
    async def _execute_step(self, step: ExecutionStep) -> bool:
        """执行单个步骤"""
        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()
        
        if self.on_step_start:
            self.on_step_start(step)
        
        try:
            # 模拟执行（实际应用中使用真实的 Skill 执行）
            # 这里使用模拟来演示流程
            await asyncio.sleep(0.5)  # 模拟执行时间
            
            # 模拟成功
            step.result = f"Mock result for {step.name}"
            step.status = StepStatus.COMPLETED
            step.end_time = datetime.now()
            
            if self.on_step_complete:
                self.on_step_complete(step, True)
            
            return True
            
        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            step.end_time = datetime.now()
            
            if self.on_step_complete:
                self.on_step_complete(step, False)
            
            return False
    
    def _check_dependencies(self, step: ExecutionStep) -> bool:
        """检查步骤依赖是否满足"""
        if not step.dependencies:
            return True
        
        for dep_id in step.dependencies:
            dep_step = self._get_step_by_id(dep_id)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                return False
        
        return True
    
    def _get_step_by_id(self, step_id: str) -> Optional[ExecutionStep]:
        """根据ID获取步骤"""
        if not self.blueprint:
            return None
        for step in self.blueprint:
            if step.id == step_id:
                return step
        return None
    
    def pause_execution(self):
        """暂停执行"""
        self.is_paused = True
        if self.current_step_index >= 0 and self.blueprint:
            step = self.blueprint[self.current_step_index]
            if step.status == StepStatus.RUNNING:
                step.status = StepStatus.PAUSED
    
    def resume_execution(self):
        """恢复执行"""
        self.is_paused = False
    
    async def resume_after_intervention(self):
        """干预后恢复执行"""
        if self.is_paused:
            self.resume_execution()
            # 从当前步骤继续
            if self.current_step_index >= 0 and self.blueprint:
                step = self.blueprint[self.current_step_index]
                if step.status == StepStatus.PAUSED:
                    step.status = StepStatus.PENDING
            
            # 继续执行剩余步骤
            await self.execute_from_current()
    
    async def execute_from_current(self) -> ExecutionResult:
        """从当前步骤继续执行"""
        if not self.blueprint or self.current_step_index < 0:
            return ExecutionResult(
                success=False,
                summary="No active execution",
                completed_steps=0,
                total_steps=0,
                failed_steps=0,
                execution_time=0.0
            )
        
        self.is_executing = True
        self.is_paused = False
        
        completed = sum(1 for s in self.blueprint if s.status == StepStatus.COMPLETED)
        failed = 0
        
        for i in range(self.current_step_index, len(self.blueprint)):
            if self.is_paused:
                break
            
            step = self.blueprint[i]
            self.current_step_index = i
            
            # 跳过已完成的步骤
            if step.status == StepStatus.COMPLETED:
                continue
            
            # 检查依赖
            if not self._check_dependencies(step):
                continue
            
            # 执行步骤
            success = await self._execute_step(step)
            
            if success:
                completed += 1
            else:
                failed += 1
                break
        
        self.is_executing = False
        
        execution_time = 0.0
        if self.execution_start_time:
            execution_time = (datetime.now() - self.execution_start_time).total_seconds()
        
        result = ExecutionResult(
            success=failed == 0,
            summary=f"Completed {completed}/{len(self.blueprint)} steps",
            completed_steps=completed,
            total_steps=len(self.blueprint),
            failed_steps=failed,
            execution_time=execution_time
        )
        
        if self.on_execution_complete:
            self.on_execution_complete(result)
        
        return result
    
    def skip_current_step(self):
        """跳过当前步骤"""
        if self.current_step_index >= 0 and self.blueprint:
            step = self.blueprint[self.current_step_index]
            step.status = StepStatus.SKIPPED
            self.abandoned_steps.append(step)
    
    def replan_from_step(self, step_index: int, new_steps: List[Dict[str, Any]]):
        """
        从指定步骤重新规划
        
        REPLAN 功能：保留已完成的步骤，替换后续步骤
        """
        if not self.blueprint:
            return
        
        # 标记被废弃的步骤
        for i in range(step_index, len(self.blueprint)):
            step = self.blueprint[i]
            if step.status != StepStatus.COMPLETED:
                step.status = StepStatus.ABORTED
                self.abandoned_steps.append(step)
        
        # 保留已完成的步骤
        completed_steps = [s for s in self.blueprint if s.status == StepStatus.COMPLETED]
        
        # 创建新步骤
        new_execution_steps = []
        for i, data in enumerate(new_steps):
            step = ExecutionStep(
                id=data.get("id", f"step_{step_index + i}"),
                name=data["name"],
                description=data.get("description", ""),
                dependencies=data.get("dependencies", []),
                metadata={**data.get("metadata", {}), "replanned": True}
            )
            new_execution_steps.append(step)
        
        # 合并
        self.blueprint = completed_steps + new_execution_steps
        self.current_step_index = len(completed_steps) - 1
        
        if self.on_blueprint_loaded:
            self.on_blueprint_loaded(self.blueprint)
    
    def get_progress(self) -> Dict[str, Any]:
        """获取执行进度"""
        if not self.blueprint:
            return {"percentage": 0, "current_step": -1, "total_steps": 0}
        
        total = len(self.blueprint)
        completed = sum(1 for s in self.blueprint if s.status == StepStatus.COMPLETED)
        percentage = int((completed / total) * 100) if total > 0 else 0
        
        return {
            "percentage": percentage,
            "current_step": self.current_step_index,
            "total_steps": total,
            "completed": completed,
            "is_executing": self.is_executing,
            "is_paused": self.is_paused
        }
    
    def get_current_step(self) -> Optional[ExecutionStep]:
        """获取当前步骤"""
        if not self.blueprint or self.current_step_index < 0:
            return None
        if self.current_step_index < len(self.blueprint):
            return self.blueprint[self.current_step_index]
        return None
    
    def get_step_status_summary(self) -> List[Dict[str, str]]:
        """获取步骤状态摘要"""
        if not self.blueprint:
            return []
        
        return [
            {
                "id": step.id,
                "name": step.name,
                "status": step.status.value
            }
            for step in self.blueprint
        ]


def create_execution_blueprint_system() -> ExecutionBlueprintSystem:
    """创建执行蓝图系统实例"""
    return ExecutionBlueprintSystem()
