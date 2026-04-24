# -*- coding: utf-8 -*-
"""
ParallelExecutor - 并行步骤执行器

- 分析步骤依赖关系图
- 按拓扑层级分组并行执行
- 并发限制控制（Semaphore）
- 结果收集和按原始顺序排序
"""
import asyncio
import time
from collections import defaultdict, deque
from typing import List, Dict, Set, Any, Optional

from blueclaw.adapter.models import ExecutionBlueprint, ExecutionStep, ExecutionResult, StepResult
from blueclaw.adapter.web.executor import WebExecutor


class ParallelExecutor:
    """Web 步骤并行执行器

    将 Blueprint 中无依赖的步骤分组，使用 asyncio.gather 并行执行。
    有依赖的步骤按拓扑顺序串行执行。
    """

    def __init__(
        self,
        executor: WebExecutor,
        max_concurrency: int = 3,
    ):
        self.executor = executor
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    def _build_dependency_graph(
        self, steps: List[ExecutionStep]
    ) -> Dict[str, Set[str]]:
        """构建步骤依赖图：step_id -> 依赖的 step_id 集合"""
        graph: Dict[str, Set[str]] = defaultdict(set)
        step_ids = {s.step_id for s in steps}

        for step in steps:
            for dep_id in step.dependencies:
                if dep_id in step_ids:
                    graph[step.step_id].add(dep_id)
        return graph

    def _group_by_levels(
        self, steps: List[ExecutionStep], graph: Dict[str, Set[str]]
    ) -> List[List[ExecutionStep]]:
        """按拓扑层级分组，同一层级内的步骤可以并行执行"""
        step_map = {s.step_id: s for s in steps}
        in_degree: Dict[str, int] = {s.step_id: 0 for s in steps}

        # 计算入度
        for step_id, deps in graph.items():
            in_degree[step_id] = len(deps)

        # BFS 分层
        levels: List[List[ExecutionStep]] = []
        remaining = set(step_map.keys())

        while remaining:
            # 找到当前入度为 0 的步骤
            current_level = [
                step_map[sid] for sid in remaining
                if in_degree.get(sid, 0) == 0
            ]
            if not current_level:
                # 有环，将剩余全部放入下一层
                current_level = [step_map[sid] for sid in remaining]
                remaining.clear()
            else:
                for step in current_level:
                    remaining.discard(step.step_id)
                    # 减少下游步骤的入度
                    for sid in remaining:
                        if step.step_id in graph.get(sid, set()):
                            in_degree[sid] = max(0, in_degree.get(sid, 0) - 1)

            levels.append(current_level)

        return levels

    async def execute_parallel(
        self,
        blueprint: ExecutionBlueprint,
        page,
    ) -> ExecutionResult:
        """并行执行 Blueprint 的所有步骤"""
        start_time = time.time()
        step_results: Dict[str, StepResult] = {}
        all_steps = blueprint.steps

        if not all_steps:
            return ExecutionResult(
                blueprint_id=blueprint.task_id,
                success=True,
                step_results=[],
            )

        # 1. 构建依赖图和层级
        graph = self._build_dependency_graph(all_steps)
        levels = self._group_by_levels(all_steps, graph)

        # 2. 按层级执行
        for level_idx, level_steps in enumerate(levels):
            if len(level_steps) == 1:
                # 单层只有一个步骤，串行执行
                step = level_steps[0]
                result = await self._execute_single_step(step, page, blueprint.task_id)
                step_results[step.step_id] = result
            else:
                # 多个步骤并行执行
                tasks = [
                    self._execute_single_step(step, page, blueprint.task_id)
                    for step in level_steps
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for step, res in zip(level_steps, results):
                    if isinstance(res, Exception):
                        step_results[step.step_id] = StepResult(
                            status="failed",
                            output="",
                            error=str(res),
                            duration_ms=0,
                        )
                    else:
                        step_results[step.step_id] = res

        # 3. 按原始步骤顺序整理结果
        ordered_results = [step_results[s.step_id] for s in all_steps]
        total_duration = (time.time() - start_time) * 1000
        all_success = all(r.status == "success" for r in ordered_results)

        return ExecutionResult(
            blueprint_id=blueprint.task_id,
            success=all_success,
            step_results=ordered_results,
            total_duration_ms=total_duration,
        )

    async def _execute_single_step(
        self, step: ExecutionStep, page, blueprint_id: str
    ) -> StepResult:
        """在信号量限制下执行单个步骤"""
        async with self._semaphore:
            return await self.executor.execute_step(step, page, blueprint_id)

    def analyze_parallel_potential(self, blueprint: ExecutionBlueprint) -> Dict[str, Any]:
        """分析蓝图的并行潜力（用于性能报告）"""
        graph = self._build_dependency_graph(blueprint.steps)
        levels = self._group_by_levels(blueprint.steps, graph)

        serial_time_estimate = sum(
            5000 + s.action.params.get("estimated_duration_ms", 5000)
            for s in blueprint.steps
        )

        # 并行估算：每层取最大值
        parallel_time_estimate = sum(
            max(
                5000 + s.action.params.get("estimated_duration_ms", 5000)
                for s in level
            )
            for level in levels
        )

        return {
            "total_steps": len(blueprint.steps),
            "levels": len(levels),
            "max_parallel_per_level": max(len(l) for l in levels) if levels else 0,
            "serial_time_estimate_ms": serial_time_estimate,
            "parallel_time_estimate_ms": parallel_time_estimate,
            "speedup_estimate": (
                serial_time_estimate / parallel_time_estimate
                if parallel_time_estimate > 0 else 1.0
            ),
            "level_breakdown": [
                {"level": i, "steps": [s.step_id for s in level]}
                for i, level in enumerate(levels)
            ],
        }
