# -*- coding: utf-8 -*-
"""
replan_engine.py - REPLAN引擎

职责: 处理干预后的重新规划
"""

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

from .blueprint_generator import ExecutionStep, StepStatus, BlueprintGenerator
from .thinking_chain import ThinkingChain, ThinkingNode


@dataclass
class ReplanResult:
    """重新规划结果"""
    success: bool
    kept_steps: List[ExecutionStep]      # 保留的步骤
    new_steps: List[ExecutionStep]       # 新生成的步骤
    removed_steps: List[ExecutionStep]   # 移除的步骤
    reason: str = ""                     # 重新规划原因


class ReplanEngine:
    """
    REPLAN引擎
    
    核心逻辑：
    - 保留已完成的步骤
    - 根据干预意图重新规划后续步骤
    """
    
    def __init__(self):
        """初始化REPLAN引擎"""
        self.blueprint_generator = BlueprintGenerator()
    
    def replan(
        self,
        all_steps: List[ExecutionStep],
        failed_step: ExecutionStep,
        intervention_context: Dict[str, Any]
    ) -> ReplanResult:
        """
        重新规划
        
        Args:
            all_steps: 所有步骤
            failed_step: 失败的步骤
            intervention_context: 干预上下文
                - action: 干预动作 (replan/skip/manual)
                - user_input: 用户输入/反馈
                - custom_requirements: 自定义需求
                
        Returns:
            ReplanResult: 重新规划结果
        """
        action = intervention_context.get('action', 'replan')
        
        if action == 'skip':
            return self._handle_skip(all_steps, failed_step)
        
        if action == 'stop':
            return self._handle_stop(all_steps, failed_step)
        
        # 默认：重新规划
        return self._handle_replan(all_steps, failed_step, intervention_context)
    
    def _handle_skip(
        self,
        all_steps: List[ExecutionStep],
        skip_step: ExecutionStep
    ) -> ReplanResult:
        """
        处理跳过步骤
        
        策略：标记步骤为SKIPPED，保留其他步骤
        """
        # 找到要跳过的步骤
        for step in all_steps:
            if step.step_id == skip_step.step_id:
                step.status = StepStatus.SKIPPED
                break
        
        # 保留所有非失败步骤
        kept_steps = [s for s in all_steps if s.status != StepStatus.FAILED]
        
        return ReplanResult(
            success=True,
            kept_steps=kept_steps,
            new_steps=[],
            removed_steps=[skip_step],
            reason=f"跳过步骤 {skip_step.name}"
        )
    
    def skip_step(self, all_steps: List[ExecutionStep], step_id: str) -> ReplanResult:
        """
        Skip a specific step
        
        Args:
            all_steps: All steps
            step_id: Step ID to skip
            
        Returns:
            ReplanResult: Skip result
        """
        skip_step = None
        for step in all_steps:
            if step.step_id == step_id:
                step.status = StepStatus.SKIPPED
                skip_step = step
                break
        
        return ReplanResult(
            success=True,
            kept_steps=[s for s in all_steps if s.status != StepStatus.SKIPPED],
            new_steps=[],
            removed_steps=[skip_step] if skip_step else [],
            reason=f"Skipped step {step_id}"
        )
    
    def stop(self, all_steps: List[ExecutionStep]) -> ReplanResult:
        """
        停止执行
        
        Args:
            all_steps: 所有步骤
            
        Returns:
            ReplanResult: 停止结果
        """
        # 标记所有未完成步骤为 SKIPPED
        for step in all_steps:
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.SKIPPED
        
        return ReplanResult(
            success=True,
            kept_steps=[s for s in all_steps if s.status == StepStatus.COMPLETED],
            new_steps=[],
            removed_steps=[s for s in all_steps if s.status == StepStatus.SKIPPED],
            reason="用户停止执行"
        )
    
    def _handle_stop(
        self,
        all_steps: List[ExecutionStep],
        stop_step: ExecutionStep
    ) -> ReplanResult:
        """
        处理停止任务
        
        策略：保留已完成步骤，移除所有未完成步骤
        """
        kept_steps = [s for s in all_steps if s.status == StepStatus.COMPLETED]
        removed_steps = [s for s in all_steps if s.status != StepStatus.COMPLETED]
        
        return ReplanResult(
            success=True,
            kept_steps=kept_steps,
            new_steps=[],
            removed_steps=removed_steps,
            reason="用户停止任务"
        )
    
    def _handle_replan(
        self,
        all_steps: List[ExecutionStep],
        failed_step: ExecutionStep,
        context: Dict[str, Any]
    ) -> ReplanResult:
        """
        处理重新规划
        
        策略：
        1. 保留已完成的步骤
        2. 分析失败原因和用户反馈
        3. 生成新的替代步骤
        """
        # 分离已完成和未完成
        kept_steps = [s for s in all_steps if s.status == StepStatus.COMPLETED]
        remaining_steps = [s for s in all_steps if s.status != StepStatus.COMPLETED]
        
        # 分析用户干预意图
        user_input = context.get('user_input', '')
        custom_requirements = context.get('custom_requirements', {})
        
        # 根据干预意图生成新步骤
        new_steps = self._generate_replacement_steps(
            failed_step,
            remaining_steps,
            user_input,
            custom_requirements
        )
        
        # 更新依赖关系
        if kept_steps and new_steps:
            # 新步骤的第一个依赖于最后一个已完成的步骤
            last_completed = kept_steps[-1]
            for step in new_steps:
                # 将原来对失败步骤的依赖改为对最后完成步骤的依赖
                step.dependencies = [
                    last_completed.step_id if dep == failed_step.step_id else dep
                    for dep in step.dependencies
                ]
        
        return ReplanResult(
            success=True,
            kept_steps=kept_steps,
            new_steps=new_steps,
            removed_steps=remaining_steps,
            reason=f"基于用户反馈重新规划: {user_input[:50]}..." if user_input else "自动重新规划"
        )
    
    def _generate_replacement_steps(
        self,
        failed_step: ExecutionStep,
        remaining_steps: List[ExecutionStep],
        user_input: str,
        custom_requirements: Dict[str, Any]
    ) -> List[ExecutionStep]:
        """
        生成替换步骤
        
        Args:
            failed_step: 失败的步骤
            remaining_steps: 剩余的原始步骤
            user_input: 用户输入
            custom_requirements: 自定义需求
            
        Returns:
            List[ExecutionStep]: 新步骤列表
        """
        # 解析用户意图
        adjustments = self._parse_user_adjustments(user_input)
        
        # 根据调整生成新步骤
        new_steps = []
        
        # 简单策略：如果用户指定了方向，替换失败步骤
        if adjustments.get('alternative_approach'):
            # 创建替代步骤
            alt_step = ExecutionStep(
                step_id=f"{failed_step.step_id}_alt",
                name=f"{failed_step.name} (调整)",
                description=f"根据用户反馈调整: {adjustments['alternative_approach']}",
                direction=adjustments['alternative_approach'],
                expected_result=failed_step.expected_result,
                validation_rule=failed_step.validation_rule,
                tool=adjustments.get('tool', failed_step.tool),
                dependencies=[]
            )
            new_steps.append(alt_step)
        
        # 保留剩余步骤（可能需要调整依赖）
        for i, step in enumerate(remaining_steps):
            if step.step_id != failed_step.step_id:
                # 复制步骤
                new_step = ExecutionStep(
                    step_id=f"{step.step_id}_replanned",
                    name=step.name,
                    description=step.description,
                    direction=step.direction,
                    expected_result=step.expected_result,
                    validation_rule=step.validation_rule,
                    tool=step.tool,
                    dependencies=[]  # 依赖稍后更新
                )
                new_steps.append(new_step)
        
        # 如果没有生成新步骤，创建一个通用调整步骤
        if not new_steps:
            new_steps.append(ExecutionStep(
                step_id=f"{failed_step.step_id}_adjusted",
                name="调整后的执行",
                description=f"根据用户反馈: {user_input[:30]}..." if user_input else "重新规划",
                direction=user_input if user_input else "继续执行",
                expected_result="完成任务",
                validation_rule="非空",
                tool="code",
                dependencies=[]
            ))
        
        return new_steps
    
    def _parse_user_adjustments(self, user_input: str) -> Dict[str, Any]:
        """
        解析用户的调整意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            Dict[str, Any]: 调整参数
        """
        adjustments = {}
        
        if not user_input:
            return adjustments
        
        # 简单关键词匹配
        if any(kw in user_input for kw in ['换', '改', '调整', '不要', 'alternative']):
            adjustments['alternative_approach'] = user_input
        
        if any(kw in user_input for kw in ['搜索', 'search', 'google']):
            adjustments['tool'] = 'search'
        
        if any(kw in user_input for kw in ['文件', 'file', '保存']):
            adjustments['tool'] = 'file'
        
        if any(kw in user_input for kw in ['代码', 'code', '程序']):
            adjustments['tool'] = 'code'
        
        return adjustments
    
    def update_thinking_chain(
        self,
        thinking_chain: ThinkingChain,
        replan_result: ReplanResult,
        reason: str
    ) -> ThinkingNode:
        """
        更新思考链，记录重新规划
        
        Args:
            thinking_chain: 思考链
            replan_result: 重新规划结果
            reason: 重新规划原因
            
        Returns:
            ThinkingNode: 新增的重新规划节点
        """
        # 废弃旧的思考分支
        if thinking_chain.current_node_id:
            thinking_chain.deprecate_branch(thinking_chain.current_node_id)
        
        # 添加重新规划节点
        new_node = thinking_chain.add_clarification_node(
            parent_node_id=thinking_chain.root_node_id,
            question=f"重新规划: {reason}",
            options=[
                {'id': 'accept', 'label': '接受新方案', 'description': '继续执行调整后的计划'},
            ]
        )
        
        return new_node
