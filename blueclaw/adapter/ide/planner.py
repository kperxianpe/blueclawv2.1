# -*- coding: utf-8 -*-
"""
ArchitecturePlanner - 架构规划器

- 解析 ExecutionBlueprint 的修改意图
- 影响范围分析（依赖反向追踪）
- 生成文件级修改任务列表
- 修改顺序规划（依赖拓扑排序）
- 冲突检测
"""
from collections import defaultdict, deque
from typing import List, Dict, Set, Any, Optional

from blueclaw.adapter.ide.models import (
    CodebaseAnalysis, ModificationPlan, ModificationTask,
)
from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep


class ArchitecturePlanner:
    """架构规划器"""

    def plan(
        self,
        blueprint: ExecutionBlueprint,
        analysis: CodebaseAnalysis,
    ) -> ModificationPlan:
        """根据蓝图和代码分析生成修改计划"""
        tasks: List[ModificationTask] = []
        affected_files: Set[str] = set()
        task_map: Dict[str, ModificationTask] = {}
        conflicts: List[str] = []

        for step in blueprint.steps:
            task = self._step_to_task(step, analysis)
            if task:
                tasks.append(task)
                task_map[task.task_id] = task
                affected_files.add(task.file_path)

        # 影响范围扩展：反向追踪依赖
        for task in list(tasks):
            for dep_file in self._find_affected_files(task.file_path, analysis):
                if dep_file not in affected_files:
                    dep_task = ModificationTask(
                        task_id=f"auto_{dep_file.replace('/', '_').replace('\\', '_')}",
                        file_path=dep_file,
                        description=f"可能受 {task.file_path} 修改影响的文件",
                        task_type="review",
                        dependencies=[task.task_id],
                    )
                    tasks.append(dep_task)
                    task_map[dep_task.task_id] = dep_task
                    affected_files.add(dep_file)

        # 冲突检测：并发修改同一文件
        file_tasks: Dict[str, List[str]] = defaultdict(list)
        for task in tasks:
            file_tasks[task.file_path].append(task.task_id)
        for file_path, task_ids in file_tasks.items():
            if len(task_ids) > 1:
                conflicts.append(
                    f"File '{file_path}' has {len(task_ids)} concurrent modifications: {task_ids}"
                )

        # 拓扑排序生成执行顺序
        execution_order = self._topological_sort(tasks)

        # 预估耗时（简单模型：每任务 5s 基线 + 每行 100ms）
        total_estimated = sum(5000 + t.estimated_lines * 100 for t in tasks)

        return ModificationPlan(
            blueprint_id=blueprint.task_id,
            tasks=tasks,
            affected_files=sorted(affected_files),
            execution_order=execution_order,
            estimated_duration_ms=total_estimated,
            conflicts=conflicts,
        )

    def _step_to_task(self, step: ExecutionStep, analysis: CodebaseAnalysis) -> Optional[ModificationTask]:
        """将 ExecutionStep 转换为 ModificationTask"""
        action_type = step.action.type
        target = step.action.target
        file_path = ""

        if target:
            file_path = target.semantic or target.selector or ""

        # 从 params 中也可能有 file_path
        if not file_path:
            file_path = step.action.params.get("file_path", "")

        task_type = "edit"
        if action_type == "open_file":
            task_type = "review"
        elif action_type == "execute_command":
            task_type = "command"

        # 估算修改行数
        estimated_lines = step.action.params.get("estimated_lines", 10)

        if not file_path and action_type in ("edit_file", "open_file", "select_text"):
            file_path = "unknown"

        if not file_path:
            return None

        return ModificationTask(
            task_id=step.step_id,
            file_path=file_path,
            description=step.name,
            task_type=task_type,
            dependencies=list(step.dependencies),
            estimated_lines=estimated_lines,
        )

    def _find_affected_files(self, file_path: str, analysis: CodebaseAnalysis) -> List[str]:
        """查找受影响的文件（简化：import 了该文件的模块）"""
        result: Set[str] = set()
        base_name = file_path.split("/")[-1].split("\\")[-1]
        name_no_ext = base_name.rsplit(".", 1)[0] if "." in base_name else base_name

        for dep in analysis.dependencies:
            # 如果某文件 import 了被修改文件的模块名
            if dep.target == name_no_ext or dep.target in file_path.replace("\\", "/"):
                result.add(dep.source)
        return sorted(result)

    def _topological_sort(self, tasks: List[ModificationTask]) -> List[str]:
        """拓扑排序任务"""
        graph: Dict[str, Set[str]] = defaultdict(set)
        in_degree: Dict[str, int] = {t.task_id: 0 for t in tasks}
        task_ids = {t.task_id for t in tasks}

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_ids:
                    graph[dep_id].add(task.task_id)
                    in_degree[task.task_id] = in_degree.get(task.task_id, 0) + 1

        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        result: List[str] = []

        while queue:
            current = queue.popleft()
            result.append(current)
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 如果还有未处理的，说明有环，追加到末尾
        for tid in task_ids:
            if tid not in result:
                result.append(tid)

        return result
