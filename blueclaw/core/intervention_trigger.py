# -*- coding: utf-8 -*-
"""
intervention_trigger.py - 干预触发器

职责: 判断是否触发干预，提供干预选项
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .blueprint_generator import ExecutionStep, StepStatus


class InterventionType(Enum):
    """干预类型"""
    REPLAN = "replan"      # 重新规划
    SKIP = "skip"          # 跳过当前步骤
    STOP = "stop"          # 停止执行
    RETRY = "retry"        # 重试
    MANUAL = "manual"      # 手动操作


@dataclass
class InterventionAction:
    """干预动作"""
    action_id: str
    action_type: InterventionType
    label: str
    description: str
    priority: int = 0  # 优先级（数字越小越优先）
    metadata: Dict[str, Any] = field(default_factory=dict)


class InterventionTrigger:
    """干预触发器"""
    
    def __init__(self, max_retries: int = 2):
        """
        初始化触发器
        
        Args:
            max_retries: 最大重试次数
        """
        self.max_retries = max_retries
        self.retry_counts: Dict[str, int] = {}  # step_id -> count
        
        # 高风险操作列表
        self.high_risk_operations = [
            'delete', 'remove', 'drop', 'truncate',
            'delete_all', '清空', '删除全部'
        ]
    
    def should_intervene(
        self,
        step: ExecutionStep,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        判断是否需要干预
        
        触发条件：
        - 步骤失败且重试次数用尽
        - 检测到高风险操作
        - 用户主动暂停
        
        Args:
            step: 当前步骤
            context: 上下文
            
        Returns:
            bool: 是否需要干预
        """
        context = context or {}
        
        # 条件1：步骤失败且重试次数用尽
        if step.status == StepStatus.FAILED:
            retry_count = self.retry_counts.get(step.step_id, 0)
            if retry_count >= self.max_retries:
                return True
        
        # 条件2：检测到高风险操作
        if self._is_high_risk_operation(step):
            return True
        
        # 条件3：用户主动暂停（通过 context 传递）
        if context.get('user_paused', False):
            return True
        
        return False
    
    def get_intervention_actions(
        self,
        step: ExecutionStep,
        context: Dict[str, Any] = None
    ) -> List[InterventionAction]:
        """
        获取可用的干预动作
        
        Args:
            step: 当前步骤
            context: 上下文
            
        Returns:
            List[InterventionAction]: 干预动作列表
        """
        actions = []
        context = context or {}
        
        # 如果还可以重试，添加重试选项
        retry_count = self.retry_counts.get(step.step_id, 0)
        if retry_count < self.max_retries and step.status == StepStatus.FAILED:
            actions.append(InterventionAction(
                action_id="retry",
                action_type=InterventionType.RETRY,
                label="重新执行",
                description=f"再次尝试（{retry_count + 1}/{self.max_retries + 1}）",
                priority=1
            ))
        
        # 重新规划
        actions.append(InterventionAction(
            action_id="replan",
            action_type=InterventionType.REPLAN,
            label="重新规划",
            description="调整后续步骤继续执行",
            priority=2
        ))
        
        # 跳过此步
        actions.append(InterventionAction(
            action_id="skip",
            action_type=InterventionType.SKIP,
            label="跳过此步",
            description="跳过当前步骤继续执行",
            priority=3
        ))
        
        # 手动操作
        actions.append(InterventionAction(
            action_id="manual",
            action_type=InterventionType.MANUAL,
            label="手动操作",
            description="暂停执行，由用户手动完成此步骤",
            priority=4
        ))
        
        # 停止任务
        actions.append(InterventionAction(
            action_id="stop",
            action_type=InterventionType.STOP,
            label="停止任务",
            description="结束当前任务",
            priority=5
        ))
        
        # 按优先级排序
        actions.sort(key=lambda x: x.priority)
        
        return actions
    
    def _is_high_risk_operation(self, step: ExecutionStep) -> bool:
        """
        检查是否是高风险操作
        
        Args:
            step: 执行步骤
            
        Returns:
            bool: 是否高风险
        """
        # 检查步骤内容
        content_to_check = f"{step.name} {step.description} {step.direction}".lower()
        
        for risk_keyword in self.high_risk_operations:
            if risk_keyword.lower() in content_to_check:
                return True
        
        return False
    
    def record_retry(self, step_id: str) -> int:
        """
        记录重试次数
        
        Args:
            step_id: 步骤ID
            
        Returns:
            int: 当前重试次数
        """
        self.retry_counts[step_id] = self.retry_counts.get(step_id, 0) + 1
        return self.retry_counts[step_id]
    
    def reset_retry_count(self, step_id: str):
        """
        重置重试次数
        
        Args:
            step_id: 步骤ID
        """
        if step_id in self.retry_counts:
            del self.retry_counts[step_id]
    
    def get_retry_count(self, step_id: str) -> int:
        """
        获取重试次数
        
        Args:
            step_id: 步骤ID
            
        Returns:
            int: 重试次数
        """
        return self.retry_counts.get(step_id, 0)
    
    def can_retry(self, step_id: str) -> bool:
        """
        检查是否还可以重试
        
        Args:
            step_id: 步骤ID
            
        Returns:
            bool: 是否可以重试
        """
        return self.retry_counts.get(step_id, 0) < self.max_retries
    
    def set_max_retries(self, max_retries: int):
        """
        设置最大重试次数
        
        Args:
            max_retries: 最大重试次数
        """
        self.max_retries = max_retries
    
    def add_high_risk_keyword(self, keyword: str):
        """
        添加高风险关键词
        
        Args:
            keyword: 关键词
        """
        if keyword not in self.high_risk_operations:
            self.high_risk_operations.append(keyword)
