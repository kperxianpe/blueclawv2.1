# -*- coding: utf-8 -*-
"""
dependency_checker.py - 依赖检查器

职责: 检查步骤依赖关系，确定可执行步骤
"""

from typing import List, Set, Dict
from .blueprint_generator import ExecutionStep, StepStatus


class DependencyChecker:
    """依赖检查器"""
    
    def check_dependencies(
        self,
        step: ExecutionStep,
        completed_steps: List[ExecutionStep]
    ) -> bool:
        """
        检查步骤依赖是否满足
        
        Args:
            step: 待检查步骤
            completed_steps: 已完成的步骤列表
            
        Returns:
            bool: True=依赖满足，可以执行；False=有未完成的依赖
        """
        if not step.dependencies:
            return True
        
        # 获取已完成步骤的ID集合
        completed_ids: Set[str] = {
            s.step_id for s in completed_steps
            if s.status == StepStatus.COMPLETED
        }
        
        # 检查所有依赖是否都已完成
        for dep_id in step.dependencies:
            if dep_id not in completed_ids:
                return False
        
        return True
    
    def get_executable_steps(
        self,
        all_steps: List[ExecutionStep],
        completed_steps: List[ExecutionStep]
    ) -> List[ExecutionStep]:
        """
        获取当前可执行的步骤（依赖已满足且状态为pending）
        
        Args:
            all_steps: 所有步骤
            completed_steps: 已完成的步骤
            
        Returns:
            List[ExecutionStep]: 可执行的步骤列表
        """
        executable = []
        
        for step in all_steps:
            # 只考虑 pending 状态的步骤
            if step.status != StepStatus.PENDING:
                continue
            
            # 检查依赖是否满足
            if self.check_dependencies(step, completed_steps):
                executable.append(step)
        
        return executable
    
    def get_dependency_chain(
        self,
        step: ExecutionStep,
        all_steps: List[ExecutionStep]
    ) -> List[str]:
        """
        获取步骤的完整依赖链
        
        Args:
            step: 目标步骤
            all_steps: 所有步骤
            
        Returns:
            List[str]: 依赖链（从根到直接依赖）
        """
        step_map = {s.step_id: s for s in all_steps}
        chain = []
        
        def get_deps_recursive(step_id: str, visited: Set[str]):
            if step_id in visited:
                return  # 避免循环依赖
            
            visited.add(step_id)
            step = step_map.get(step_id)
            
            if not step:
                return
            
            for dep_id in step.dependencies:
                get_deps_recursive(dep_id, visited)
                if dep_id not in chain:
                    chain.append(dep_id)
        
        get_deps_recursive(step.step_id, set())
        return chain
    
    def check_circular_dependencies(
        self,
        all_steps: List[ExecutionStep]
    ) -> List[List[str]]:
        """
        检查循环依赖
        
        Args:
            all_steps: 所有步骤
            
        Returns:
            List[List[str]]: 发现的循环依赖列表
        """
        step_map = {s.step_id: s for s in all_steps}
        cycles = []
        
        def dfs(step_id: str, path: List[str], visited: Set[str]):
            if step_id in path:
                # 发现循环
                cycle_start = path.index(step_id)
                cycles.append(path[cycle_start:] + [step_id])
                return
            
            if step_id in visited:
                return
            
            visited.add(step_id)
            path.append(step_id)
            
            step = step_map.get(step_id)
            if step:
                for dep_id in step.dependencies:
                    dfs(dep_id, path.copy(), visited)
        
        for step in all_steps:
            dfs(step.step_id, [], set())
        
        # 去重
        unique_cycles = []
        for cycle in cycles:
            normalized = tuple(sorted(cycle[:-1]))  # 排除最后一个重复元素
            if normalized not in [tuple(sorted(c[:-1])) for c in unique_cycles]:
                unique_cycles.append(cycle)
        
        return unique_cycles
    
    def get_execution_order(
        self,
        all_steps: List[ExecutionStep]
    ) -> List[ExecutionStep]:
        """
        获取拓扑排序后的执行顺序
        
        Args:
            all_steps: 所有步骤
            
        Returns:
            List[ExecutionStep]: 排序后的步骤
        """
        step_map = {s.step_id: s for s in all_steps}
        in_degree: Dict[str, int] = {s.step_id: 0 for s in all_steps}
        
        # 计算入度
        for step in all_steps:
            for dep_id in step.dependencies:
                if dep_id in in_degree:
                    in_degree[step.step_id] += 1
        
        # Kahn算法
        queue = [sid for sid, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current_id = queue.pop(0)
            result.append(step_map[current_id])
            
            # 找到依赖于当前步骤的步骤
            for step in all_steps:
                if current_id in step.dependencies:
                    in_degree[step.step_id] -= 1
                    if in_degree[step.step_id] == 0:
                        queue.append(step.step_id)
        
        return result
    
    def are_all_dependencies_met(
        self,
        all_steps: List[ExecutionStep]
    ) -> bool:
        """
        检查是否所有步骤的依赖都已满足（用于验证蓝图有效性）
        
        Args:
            all_steps: 所有步骤
            
        Returns:
            bool: 是否所有依赖都有效
        """
        step_ids = {s.step_id for s in all_steps}
        
        for step in all_steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    return False
        
        return True
