# -*- coding: utf-8 -*-
"""
step_executor.py - 步骤执行引擎

职责: 执行每个步骤，调用对应 Skill
"""

from typing import Callable, Optional, Dict, Any, List
import asyncio
import time
from dataclasses import dataclass

from .blueprint_generator import ExecutionStep, StepStatus


class SkillHandler:
    """Skill handler base class"""
    
    async def run(self, **kwargs) -> Any:
        """
        Execute the skill
        
        Returns:
            SkillResult-like object with success, data, error, metadata attributes
        """
        raise NotImplementedError("Skill must implement run()")


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    step_id: str
    output: Any = None
    error: str = ""
    duration_ms: float = 0.0


class StepExecutor:
    """步骤执行引擎"""
    
    def __init__(self):
        """初始化执行引擎"""
        self.skills: Dict[str, Any] = {}  # 注册的skill
        self.on_step_start: Optional[Callable[[ExecutionStep], None]] = None
        self.on_step_complete: Optional[Callable[[ExecutionStep, ExecutionResult], None]] = None
        self.on_step_failed: Optional[Callable[[ExecutionStep, ExecutionResult], None]] = None
    
    def register_skill(self, name: str, skill_instance: Any) -> None:
        """
        注册Skill
        
        Args:
            name: Skill 名称
            skill_instance: Skill 实例
        """
        self.skills[name] = skill_instance
    
    def register_skills(self, skills: Dict[str, Any]) -> None:
        """
        批量注册 Skills
        
        Args:
            skills: Skill 字典
        """
        self.skills.update(skills)
    
    async def execute_step(
        self,
        step: ExecutionStep,
        context: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        执行单个步骤
        
        Args:
            step: 执行步骤
            context: 上下文信息
            
        Returns:
            ExecutionResult: 执行结果
        """
        context = context or {}
        start_time = time.time()
        
        # 触发开始回调
        if self.on_step_start:
            await self._trigger_callback(self.on_step_start, step)
        
        step.status = StepStatus.RUNNING
        step.started_at = self._get_timestamp()
        
        try:
            # 获取对应skill
            skill = self.skills.get(step.tool)
            if not skill:
                raise ValueError(f"Unknown skill: {step.tool}")
            
            # 执行skill
            skill_result = await skill.run(
                direction=step.direction,
                expected_result=step.expected_result,
                context=context
            )
            
            # 验证结果
            is_valid = self._validate_result(skill_result.data, step.validation_rule)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if skill_result.success and is_valid:
                step.status = StepStatus.COMPLETED
                step.output = {"data": skill_result.data, "metadata": skill_result.metadata}
                step.completed_at = self._get_timestamp()
                
                result = ExecutionResult(
                    success=True,
                    step_id=step.step_id,
                    output=skill_result.data,
                    duration_ms=duration_ms
                )
                
                # 触发完成回调
                if self.on_step_complete:
                    await self._trigger_callback(self.on_step_complete, step, result)
                
            else:
                error_msg = skill_result.error if not skill_result.success else "Validation failed"
                step.status = StepStatus.FAILED
                step.error = error_msg
                
                result = ExecutionResult(
                    success=False,
                    step_id=step.step_id,
                    error=error_msg,
                    duration_ms=duration_ms
                )
                
                # 触发失败回调
                if self.on_step_failed:
                    await self._trigger_callback(self.on_step_failed, step, result)
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            step.status = StepStatus.FAILED
            step.error = str(e)
            
            result = ExecutionResult(
                success=False,
                step_id=step.step_id,
                error=str(e),
                duration_ms=duration_ms
            )
            
            # 触发失败回调
            if self.on_step_failed:
                await self._trigger_callback(self.on_step_failed, step, result)
            
            return result
    
    async def execute_steps(
        self,
        steps: List[ExecutionStep],
        context: Dict[str, Any] = None,
        stop_on_error: bool = True
    ) -> List[ExecutionResult]:
        """
        执行多个步骤
        
        Args:
            steps: 步骤列表
            context: 上下文
            stop_on_error: 出错时是否停止
            
        Returns:
            List[ExecutionResult]: 执行结果列表
        """
        results = []
        
        for step in steps:
            result = await self.execute_step(step, context)
            results.append(result)
            
            if not result.success and stop_on_error:
                break
        
        return results
    
    def _validate_result(self, result: Any, rule: str) -> bool:
        """
        验证执行结果
        
        Args:
            result: 结果数据
            rule: 验证规则
            
        Returns:
            bool: 是否通过验证
        """
        if rule == "非空":
            return result is not None and result != ""
        
        if rule == "无错误":
            return True  # 错误状态由 exception 捕获
        
        if rule == "语法正确":
            # 简单检查：如果是代码，尝试解析
            if isinstance(result, str):
                try:
                    compile(result, '<string>', 'exec')
                    return True
                except SyntaxError:
                    return False
            return True
        
        if rule == "符合预期":
            # 这里可以添加更复杂的验证逻辑
            return result is not None
        
        return True
    
    async def _trigger_callback(self, callback, *args):
        """触发回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            print(f"Callback error: {e}")
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_skill_list(self) -> List[str]:
        """获取已注册的 Skill 列表"""
        return list(self.skills.keys())
    
    def has_skill(self, name: str) -> bool:
        """检查是否有指定的 Skill"""
        return name in self.skills
