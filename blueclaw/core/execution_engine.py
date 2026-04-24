#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution Engine - Complete implementation

Features:
- Blueprint creation from thinking path
- Step execution with dependencies
- Pause/Resume
- REPLAN (regenerate from failed step)
- Position tracking for visualization
- Week 20.5: Tool binding and smart selection
"""

import json
import asyncio
import time
import os
import tempfile
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

# Week 20.5 imports
try:
    from backend.tools.models import ToolBinding
except ImportError:
    # Fallback definition if backend.tools not available
    @dataclass
    class ToolBinding:
        tool_icon_id: str
        locked: bool = True
        actual_execution: Optional[Dict] = None
        
        def to_dict(self):
            return {
                "tool_icon_id": self.tool_icon_id,
                "locked": self.locked,
                "actual_execution": self.actual_execution
            }


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    SKIPPED = "skipped"
    DEPRECATED = "deprecated"  # REPLAN后废弃


@dataclass
class ExecutionStep:
    """执行步骤 - 支持可视化位置 + Week 20.5 工具绑定 + 分支汇合标记"""
    id: str
    name: str
    description: str
    direction: str
    example: str
    validation: str
    tool: str
    dependencies: List[str] = field(default_factory=list)
    status: StepStatus = field(default=StepStatus.PENDING)
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_count: int = 0
    position: Dict[str, int] = field(default_factory=dict)
    
    # Week 20.5 新增：工具绑定和提示
    tool_binding: Optional['ToolBinding'] = None  # 工具图标绑定
    tool_hint: Optional[str] = None               # 工具提示（用于智能选择）
    
    # Week 21 新增：绑定的 Adapter 列表
    attached_adapters: List[Dict] = field(default_factory=list)  # 右上角显示的 Adapter
    
    # 分支汇合可视化标记
    is_main_path: bool = True
    is_convergence: bool = False
    convergence_type: Optional[str] = None  # 'parallel' | 'sequential'
    
    def __post_init__(self):
        if not self.position:
            self.position = {"x": 100, "y": 400}
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "direction": self.direction,
            "example": self.example,
            "validation": self.validation,
            "tool": self.tool,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "failed_count": self.failed_count,
            "position": self.position,
            "tool_binding": self.tool_binding.to_dict() if self.tool_binding else None,
            "tool_hint": self.tool_hint,
            "attached_adapters": self.attached_adapters,  # Week 21
            "is_main_path": self.is_main_path,
            "is_convergence": self.is_convergence,
            "convergence_type": self.convergence_type,
        }


@dataclass
class ExecutionBlueprint:
    """执行蓝图"""
    id: str
    task_id: str
    steps: List[ExecutionStep]
    status: StepStatus = field(default=StepStatus.PENDING)
    current_step_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "current_step_id": self.current_step_id,
            "created_at": self.created_at
        }


class CancellationToken:
    """可取消令牌 - 支持级联取消传播"""
    
    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self._cancelled = False
        self._children: List['CancellationToken'] = []
    
    def cancel(self) -> None:
        """取消自身并级联取消所有子 token"""
        if self._cancelled:
            return
        self._cancelled = True
        for child in self._children:
            child.cancel()
    
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def validate(self) -> None:
        """如果已取消，抛出 CancelledError"""
        if self._cancelled:
            raise asyncio.CancelledError(f"Token {self.owner_id} was cancelled")
    
    def add_child(self, token: 'CancellationToken') -> None:
        self._children.append(token)
        # 如果父已经被取消，子也立即取消
        if self._cancelled:
            token.cancel()
    
    def remove_child(self, token: 'CancellationToken') -> None:
        if token in self._children:
            self._children.remove(token)


class StepExecutionError(Exception):
    """步骤执行错误 - 支持分类与可恢复性判定"""
    
    def __init__(
        self,
        error_type: str,
        recoverable: bool,
        context: Dict[str, Any],
        original: Optional[Exception] = None
    ):
        self.error_type = error_type
        self.recoverable = recoverable
        self.context = context
        self.original = original
        super().__init__(f"[{error_type}] recoverable={recoverable}: {context}")


class ExecutionEngine:
    """执行引擎 - Week 20.5 扩展支持工具绑定 + Token 级联取消"""
    
    def __init__(self):
        self.blueprints: Dict[str, ExecutionBlueprint] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._paused: Dict[str, bool] = {}
        self._step_tasks: Dict[str, List[asyncio.Task]] = {}
        self._blueprint_tokens: Dict[str, CancellationToken] = {}
        self._step_tokens: Dict[str, CancellationToken] = {}
        
        # Week 20.5: 工具注册表（延迟初始化）
        self._tool_registry = None
        self._tool_selector = None
        
        # Week 30.5: Adapter 截图推送（延迟初始化）
        self._adapter_mgr = None
    
    def _get_adapter_mgr(self):
        """延迟初始化 AdapterManager"""
        if self._adapter_mgr is None:
            try:
                from blueclaw.adapter.manager import AdapterManager
                self._adapter_mgr = AdapterManager()
            except ImportError:
                print("[ExecutionEngine] AdapterManager not available")
                self._adapter_mgr = None
        return self._adapter_mgr
    
    async def _maybe_capture_screenshot(self, blueprint: ExecutionBlueprint, step: ExecutionStep):
        """尝试截图并推送（WebAdapter 或 Skill 浏览器）"""
        mgr = self._get_adapter_mgr()
        if not mgr:
            return
        
        # FIX: 如果 task_id 未注册，尝试自动注册并初始化 WebAdapter
        if blueprint.task_id not in getattr(mgr, '_task_adapter_map', {}):
            try:
                from blueclaw.adapter.models import ExecutionBlueprint as AdapterBP
                adapter_bp = AdapterBP(
                    task_id=blueprint.task_id,
                    adapter_type="web",
                    steps=[],
                    config={"extra": {"viewport": {"width": 1280, "height": 720}}}
                )
                adapter = mgr.get_adapter("web")
                if getattr(adapter, '_page', None) is None:
                    await adapter.init(adapter_bp)
                    print(f"[ExecutionEngine] WebAdapter auto-initialized for {blueprint.task_id}")
                mgr._task_adapter_map[blueprint.task_id] = "web"
            except Exception as e:
                print(f"[ExecutionEngine] WebAdapter auto-init skipped: {e}")
        
        try:
            b64 = await mgr.screenshot(blueprint.task_id)
            if b64:
                from blueclaw.core.state_sync import state_sync
                await state_sync.push_screenshot(
                    blueprint.task_id,
                    step.id if hasattr(step, 'id') else step.get('id', ''),
                    b64,
                    adapter_id=blueprint.task_id
                )
                print(f"[ExecutionEngine] Screenshot pushed for step {step.name}")
            else:
                print(f"[ExecutionEngine] Screenshot empty for step {step.name} (browser not ready)")
        except Exception as e:
            print(f"[ExecutionEngine] Screenshot failed for step {step.name}: {e}")
    
    def _get_tool_registry(self):
        """延迟初始化工具注册表"""
        if self._tool_registry is None:
            try:
                from backend.tools.registry import tool_registry
                self._tool_registry = tool_registry
            except ImportError:
                print("[ExecutionEngine] ToolRegistry not available")
                self._tool_registry = None
        return self._tool_registry
    
    def _get_tool_selector(self):
        """延迟初始化工具选择器"""
        if self._tool_selector is None:
            try:
                from backend.core.tool_selector import ToolSelector
                self._tool_selector = ToolSelector()
            except ImportError:
                print("[ExecutionEngine] ToolSelector not available")
                self._tool_selector = None
        return self._tool_selector
    
    def _classify_error(self, e: Exception) -> StepExecutionError:
        """对异常进行智能分类，区分可恢复与不可恢复错误"""
        import httpx
        
        if isinstance(e, asyncio.TimeoutError):
            return StepExecutionError("timeout", True, {"message": str(e)}, e)
        if isinstance(e, (ConnectionError, httpx.ConnectError, httpx.NetworkError, httpx.ReadTimeout)):
            return StepExecutionError("network", True, {"message": str(e)}, e)
        if isinstance(e, asyncio.CancelledError):
            return StepExecutionError("cancelled", False, {"message": str(e)}, e)
        if isinstance(e, StepExecutionError):
            return e
        if isinstance(e, (ValueError, KeyError, TypeError, AttributeError, IndexError)):
            return StepExecutionError("logic", False, {"message": str(e)}, e)
        return StepExecutionError("unknown", False, {"message": str(e)}, e)
    
    async def _handle_step_failure(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        error: StepExecutionError,
        token: Optional[CancellationToken] = None
    ):
        """统一处理步骤失败：记录、通知、触发治理介入"""
        import traceback
        
        print(f"[EXEC] Step final failure {step.name}: {error.error_type} (recoverable={error.recoverable})")
        
        if not error.recoverable and error.error_type != "cancelled":
            traceback.print_exc()
        
        step.error = f"[{error.error_type}] {error.context.get('message', str(error))}"
        step.status = StepStatus.FAILED
        
        # 推送真实失败事件，携带 error_type 与脱敏栈迹
        stack_trace = traceback.format_exc() if not error.recoverable else ""
        await self._notify_step_failed(blueprint, step, error_type=error.error_type, stack_trace=stack_trace)
        
        # 治理介入联动：同一 Blueprint 累计失败 >= 2 时触发干预
        failed_count = sum(1 for s in blueprint.steps if s.status == StepStatus.FAILED)
        if failed_count >= 2:
            try:
                await self._notify_intervention_needed(blueprint, step)
            except Exception as notify_err:
                print(f"[Execution] Failed to notify intervention needed: {notify_err}")
    
    async def create_blueprint(self, task_id: str, thinking_path: List[dict]) -> ExecutionBlueprint:
        """从思考路径生成执行蓝图"""
        from blueclaw.llm import LLMClient, Message
        from blueclaw.llm.prompts import format_execution_steps_prompt
        
        prompt = format_execution_steps_prompt(thinking_path)
        
        try:
            response = await LLMClient().chat_completion(
                [
                    Message(role="system", content="You are a task planner. Output valid JSON only."),
                    Message(role="user", content=prompt)
                ]
            )
            
            # 提取 JSON（处理 Markdown 代码块）
            content = response.content.strip()
            print(f"[create_blueprint] LLM raw response length: {len(content)}")
            print(f"[create_blueprint] LLM raw preview: {content[:500]}")
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            steps_data = result.get("steps", [])
            print(f"[create_blueprint] Parsed {len(steps_data)} steps from LLM")
        except Exception as e:
            print(f"[create_blueprint] LLM error, using defaults: {e}")
            import traceback
            traceback.print_exc()
            steps_data = self._create_default_steps(thinking_path)
        
        # 创建步骤对象
        steps = []
        name_to_id = {}
        for i, step_data in enumerate(steps_data):
            step_id = f"step_{uuid.uuid4().hex[:8]}"
            step = ExecutionStep(
                id=step_id,
                name=step_data.get("name", f"步骤{i+1}"),
                description=step_data.get("description", ""),
                direction=step_data.get("direction", ""),
                example=step_data.get("example", ""),
                validation=step_data.get("validation", ""),
                tool=step_data.get("tool", "Skill"),
                dependencies=step_data.get("dependencies", []),
                position={"x": 100 + i * 250, "y": 400}
            )
            steps.append(step)
            name_to_id[step.name] = step_id
        
        # 将 LLM 生成的基于名称的依赖转换为基于 ID 的依赖
        for step in steps:
            resolved_deps = []
            for dep in step.dependencies:
                if dep in name_to_id:
                    resolved_deps.append(name_to_id[dep])
                elif any(s.id == dep for s in steps):
                    resolved_deps.append(dep)
                else:
                    # 无法解析的依赖，忽略或链接到前一个有效步骤
                    pass
            step.dependencies = resolved_deps
        
        self._resolve_dependencies(steps)
        
        # 计算 DAG 分支布局 + 主路径/汇合标记
        self._compute_branch_layout(steps)
        
        # 自动为特定步骤绑定工具（加装 skill）
        for step in steps:
            lowered = step.name.lower()
            bound_tool = None
            if any(k in lowered for k in ["价格", "预算", "费用", "查询", "搜索", "查"]):
                bound_tool = "skill-search"
            elif any(k in lowered for k in ["文档", "报告", "攻略", "写入", "保存", "生成文件", "写文件"]):
                bound_tool = "skill-file"
            elif any(k in lowered for k in ["读取", "获取文件", "读文件"]):
                bound_tool = "skill-file"
            
            if bound_tool:
                step.tool_binding = ToolBinding(
                    tool_icon_id=bound_tool,
                    locked=True
                )
                print(f"[create_blueprint] Auto-bound tool '{bound_tool}' to step '{step.name}'")
        
        blueprint = ExecutionBlueprint(
            id=f"blueprint_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            steps=steps
        )
        
        self.blueprints[blueprint.id] = blueprint
        return blueprint
    
    def get_blueprint_by_task_id(self, task_id: str) -> Optional[ExecutionBlueprint]:
        """通过 task_id 查找蓝图"""
        for blueprint in self.blueprints.values():
            if blueprint.task_id == task_id:
                return blueprint
        return None
    
    async def start_execution(self, blueprint_id: str) -> bool:
        """开始执行"""
        blueprint = self.blueprints.get(blueprint_id)
        # 如果找不到，尝试通过 task_id 查找（用于前端只发送 task_id 的情况）
        if not blueprint and blueprint_id.startswith("task_"):
            blueprint = self.get_blueprint_by_task_id(blueprint_id)
            if blueprint:
                blueprint_id = blueprint.id
        
        if not blueprint or blueprint_id in self.running_tasks:
            return False
        
        blueprint.status = StepStatus.RUNNING
        blueprint.started_at = datetime.now().isoformat()
        self._paused[blueprint_id] = False
        
        # 创建取消 token
        token = CancellationToken(f"blueprint:{blueprint_id}")
        self._blueprint_tokens[blueprint_id] = token
        self._step_tasks[blueprint_id] = []
        
        task = asyncio.create_task(self._execute_blueprint(blueprint_id))
        self.running_tasks[blueprint_id] = task
        return True
    
    def cancel_execution(self, blueprint_id: str) -> bool:
        """取消蓝图的执行，级联取消所有子 step task"""
        print(f"[Execution] Cancelling execution for blueprint {blueprint_id}")
        
        # 1. 标记蓝图 token 取消（级联传播到所有子 token）
        token = self._blueprint_tokens.get(blueprint_id)
        if token:
            token.cancel()
        
        # 2. 取消主执行 task
        main_task = self.running_tasks.get(blueprint_id)
        if main_task and not main_task.done():
            main_task.cancel()
        
        # 3. 取消所有子 step task
        step_tasks = self._step_tasks.get(blueprint_id, [])
        cancelled_count = 0
        for step_task in step_tasks:
            if not step_task.done():
                step_task.cancel()
                cancelled_count += 1
        
        if cancelled_count > 0:
            print(f"[Execution] Cancelled {cancelled_count} step tasks for blueprint {blueprint_id}")
        
        # 4. 清理记录
        self._step_tasks.pop(blueprint_id, None)
        self.running_tasks.pop(blueprint_id, None)
        self._paused.pop(blueprint_id, None)
        self._blueprint_tokens.pop(blueprint_id, None)
        # 清理 step token
        step_ids_to_remove = [sid for sid, tok in self._step_tokens.items() if tok.owner_id.startswith(f"step:{blueprint_id}:")]
        for sid in step_ids_to_remove:
            self._step_tokens.pop(sid, None)
        return True
    
    async def _execute_blueprint(self, blueprint_id: str):
        """执行蓝图协程（带并发控制）"""
        blueprint = self.blueprints.get(blueprint_id)
        if not blueprint:
            print(f"[Execution] Blueprint not found: {blueprint_id}")
            return
        
        # Week 30.5 FIX: 自动初始化 WebAdapter（如果蓝图包含 Web 步骤）
        web_adapter_initialized = False
        mgr = self._get_adapter_mgr()
        if mgr:
            has_web_step = any(
                (s.tool if hasattr(s, 'tool') else s.get('tool', '')) in ('Browser', 'Web', 'browser', 'web')
                for s in blueprint.steps
            )
            if has_web_step:
                try:
                    from blueclaw.adapter.models import ExecutionBlueprint as AdapterBP
                    adapter_bp = AdapterBP(
                        task_id=blueprint.task_id,
                        adapter_type="web",
                        steps=[],
                        config={"extra": {"viewport": {"width": 1280, "height": 720}}}
                    )
                    adapter = mgr.get_adapter("web")
                    # 避免重复初始化
                    if getattr(adapter, '_page', None) is None:
                        await adapter.init(adapter_bp)
                        print(f"[ExecutionEngine] WebAdapter initialized for task {blueprint.task_id}")
                    mgr._task_adapter_map[blueprint.task_id] = "web"
                    web_adapter_initialized = True
                except Exception as e:
                    print(f"[ExecutionEngine] WebAdapter init warning: {e}")
        
        try:
            # 使用 gather 并行执行所有可执行的步骤
            await self._execute_steps_parallel(blueprint, blueprint_id)
            
            # 检查是否全部完成
            active_steps = [s for s in blueprint.steps if s.status != StepStatus.DEPRECATED]
            
            # 最终同步：确保所有步骤状态都通知到前端
            await self._sync_all_step_states(blueprint, active_steps)
            
            if all(s.status == StepStatus.COMPLETED for s in active_steps):
                blueprint.status = StepStatus.COMPLETED
                blueprint.completed_at = datetime.now().isoformat()
                await self._notify_completed(blueprint)
            elif blueprint.status != StepStatus.PAUSED:
                blueprint.status = StepStatus.FAILED
                
        except asyncio.CancelledError:
            print(f"[Execution] Blueprint {blueprint_id} cancelled")
            blueprint.status = StepStatus.SKIPPED
        except Exception as e:
            print(f"[Execution] Blueprint execution error: {e}")
            import traceback
            traceback.print_exc()
            blueprint.status = StepStatus.FAILED
        finally:
            # 确保清理
            if blueprint_id in self.running_tasks:
                del self.running_tasks[blueprint_id]
            if blueprint_id in self._paused:
                del self._paused[blueprint_id]
            if blueprint_id in self._step_tasks:
                del self._step_tasks[blueprint_id]
            # Note: WebAdapter cleanup is deferred to task.cancel or explicit cleanup
            # to allow freeze_request screenshot after execution completes
            print(f"[Execution] Blueprint {blueprint_id} finished with status: {blueprint.status}")
    
    async def _execute_steps_parallel(self, blueprint: ExecutionBlueprint, blueprint_id: str):
        """智能执行步骤（无依赖的并行，有依赖的顺序）"""
        pending_steps = [s for s in blueprint.steps 
                        if s.status not in [StepStatus.COMPLETED, StepStatus.DEPRECATED, StepStatus.SKIPPED]]
        
        # 分离有依赖和无依赖的步骤
        independent_steps = [s for s in pending_steps if not s.dependencies]
        dependent_steps = [s for s in pending_steps if s.dependencies]
        
        with open("exec_debug.log", "a", encoding="utf-8") as dbg:
            dbg.write(f"[EXEC] Blueprint {blueprint_id}: {len(independent_steps)} independent, {len(dependent_steps)} dependent\n")
            for s in independent_steps:
                dbg.write(f"[EXEC] Independent: {s.name} (deps={s.dependencies})\n")
            for s in dependent_steps:
                dbg.write(f"[EXEC] Dependent: {s.name} (deps={s.dependencies})\n")
        
        # 1. 先并行执行所有无依赖步骤
        if independent_steps:
            log_msg = f"[Execution] Executing {len(independent_steps)} independent steps in parallel"
            print(log_msg)
            tasks = []
            blueprint_token = self._blueprint_tokens.get(blueprint_id)
            for step in independent_steps:
                if self._paused.get(blueprint_id, False):
                    break
                # 检查蓝图 token 是否已取消
                if blueprint_token and blueprint_token.is_cancelled:
                    print(f"[Execution] Blueprint {blueprint_id} token cancelled, skip step {step.name}")
                    break
                # 为每个 step 创建子 token
                step_token = CancellationToken(f"step:{blueprint_id}:{step.id}")
                if blueprint_token:
                    blueprint_token.add_child(step_token)
                self._step_tokens[step.id] = step_token
                
                task = asyncio.create_task(self._execute_step_with_isolation(blueprint, step, step_token))
                tasks.append(task)
                if blueprint_id not in self._step_tasks:
                    self._step_tasks[blueprint_id] = []
                self._step_tasks[blueprint_id].append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # 2. 再顺序执行有依赖的步骤
        blueprint_token = self._blueprint_tokens.get(blueprint_id)
        for step in dependent_steps:
            if self._paused.get(blueprint_id, False):
                break
            
            # 检查是否已被取消
            if blueprint_token and blueprint_token.is_cancelled:
                print(f"[Execution] Blueprint {blueprint_id} token cancelled, stopping dependent step {step.name}")
                break
            if blueprint_id not in self.running_tasks:
                print(f"[Execution] Blueprint {blueprint_id} cancelled, stopping dependent step {step.name}")
                break
            
            with open("exec_debug.log", "a", encoding="utf-8") as dbg:
                dbg.write(f"[EXEC] Waiting dependencies for: {step.name}\n")
            
            # 等待依赖完成（轮询中检查取消）
            if not self._check_dependencies_satisfied(blueprint, step):
                await self._wait_for_dependencies_with_token(blueprint, step, blueprint_token)
            
            with open("exec_debug.log", "a", encoding="utf-8") as dbg:
                dbg.write(f"[EXEC] Dependencies satisfied for: {step.name}, executing...\n")
            
            # 再次检查取消状态
            if blueprint_token and blueprint_token.is_cancelled:
                print(f"[Execution] Blueprint {blueprint_id} token cancelled, skipping dependent step {step.name}")
                break
            if blueprint_id not in self.running_tasks:
                print(f"[Execution] Blueprint {blueprint_id} cancelled, skipping dependent step {step.name}")
                break
            
            # 为依赖步骤创建子 token
            step_token = CancellationToken(f"step:{blueprint_id}:{step.id}")
            if blueprint_token:
                blueprint_token.add_child(step_token)
            self._step_tokens[step.id] = step_token
            
            blueprint.current_step_id = step.id
            await self._execute_step_with_isolation(blueprint, step, step_token)
            # 失败处理与干预触发已统一收拢到 _execute_step -> _handle_step_failure
    
    async def _execute_step_with_isolation(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        token: Optional[CancellationToken] = None
    ):
        """带异常隔离的步骤执行（支持 Token 取消）"""
        # 检查是否已被取消
        if blueprint.id not in self.running_tasks:
            print(f"[Execution] Step {step.name} skipped because blueprint {blueprint.id} was cancelled")
            step.status = StepStatus.SKIPPED
            return
        if token and token.is_cancelled:
            print(f"[Execution] Step {step.name} skipped because token was cancelled")
            step.status = StepStatus.SKIPPED
            return
        
        try:
            await self._execute_step(blueprint, step, token)
        except asyncio.CancelledError:
            print(f"[Execution] Step {step.name} cancelled")
            step.status = StepStatus.SKIPPED
            raise
        # 其他异常已在 _execute_step 内统一处理（重试/分类/上报/治理联动），此处不再重复捕获
    
    async def _execute_step(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        token: Optional[CancellationToken] = None
    ):
        """执行单个步骤 - Week 20.5 支持工具绑定（带超时保护+可靠通知+Token 取消）"""
        import traceback
        
        def _dbg(msg):
            print(msg)
        
        _dbg(f"[EXEC] Starting step: {step.name} (id={step.id})")
        
        # 启动前检查 token
        if token:
            token.validate()
        
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        
        # 通知前端步骤开始
        try:
            await self._notify_step_started(blueprint, step)
        except Exception as e:
            _dbg(f"[EXEC] Failed to notify step started: {e}")
        
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # 添加超时保护，防止步骤卡住（30s 足够 LLM 响应，同时更快释放资源）
                _dbg(f"[EXEC] Calling _execute_step_internal for: {step.name} (attempt {attempt})")
                
                if token:
                    token.validate()
                
                result = await asyncio.wait_for(
                    self._execute_step_internal(blueprint, step, token),
                    timeout=30.0
                )
                
                # 执行完立刻检查 token
                if token:
                    token.validate()
                
                _dbg(f"[EXEC] Result for {step.name}: {result}")
                
                # 如果 bound tool 执行失败，fallback 到 LLM
                if not result.get("success") and step.tool_binding:
                    _dbg(f"[EXEC] Bound tool failed for {step.name}, falling back to LLM")
                    if token:
                        token.validate()
                    result = await self._execute_step_legacy(blueprint, step, token)
                    if token:
                        token.validate()
                
                if result.get("success"):
                    step.result = result.get("result", f"成功执行: {step.name}")
                    step.status = StepStatus.COMPLETED
                    _dbg(f"[EXEC] Step completed: {step.name}")
                    # 重试通知确保送达
                    await self._notify_with_retry(blueprint, step, "completed")
                    # Week 30.5: Web 步骤截图推送
                    await self._maybe_capture_screenshot(blueprint, step)
                    break  # 成功，跳出重试循环
                else:
                    raise StepExecutionError(
                        "execution_failed", False,
                        {"message": result.get("error", "执行失败")}
                    )
                    
            except asyncio.TimeoutError as e:
                error = self._classify_error(e)
                last_error = error
                step.failed_count += 1
                if error.recoverable and attempt < max_retries:
                    _dbg(f"[EXEC] Step timeout for {step.name}, retrying ({attempt+1}/{max_retries}) after 1s")
                    await asyncio.sleep(1.0)
                    continue
                await self._handle_step_failure(blueprint, step, error, token)
                break
            except asyncio.CancelledError:
                _dbg(f"[EXEC] Step cancelled during execution: {step.name}")
                step.status = StepStatus.SKIPPED
                raise
            except Exception as e:
                if isinstance(e, StepExecutionError):
                    error = e
                else:
                    error = self._classify_error(e)
                last_error = error
                step.failed_count += 1
                if error.recoverable and attempt < max_retries:
                    _dbg(f"[EXEC] Step error in {step.name}: {error.error_type}, retrying ({attempt+1}/{max_retries}) after 1s")
                    await asyncio.sleep(1.0)
                    continue
                await self._handle_step_failure(blueprint, step, error, token)
                break
        
        step.completed_at = datetime.now().isoformat()
        _dbg(f"[EXEC] Finished step: {step.name} with status {step.status}")
    
    async def _notify_with_retry(self, blueprint: ExecutionBlueprint, step: ExecutionStep, status: str, max_retries: int = 3):
        """带重试的状态通知"""
        for attempt in range(max_retries):
            try:
                if status == "completed":
                    await self._notify_step_completed(blueprint, step)
                elif status == "failed":
                    await self._notify_step_failed(blueprint, step)
                else:
                    await self._notify_step_started(blueprint, step)
                return  # 通知成功
            except Exception as e:
                print(f"[Execution] Notify attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))  # 指数退避
                else:
                    print(f"[Execution] Notify failed after {max_retries} attempts")
    
    async def _execute_step_internal(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        token: Optional[CancellationToken] = None
    ) -> Dict[str, Any]:
        """步骤执行内部逻辑"""
        # Week 20.5: 检查是否有工具绑定，使用新的执行逻辑
        registry = self._get_tool_registry()
        has_tool_binding = step.tool_binding and step.tool_binding.locked
        
        if registry and has_tool_binding:
            # 有工具绑定，使用新逻辑
            return await self._execute_step_with_binding(blueprint, step, token)
        else:
            # 旧版执行逻辑（兼容模式）
            return await self._execute_step_legacy(blueprint, step, token)
    
    async def _execute_step_legacy(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        token: Optional[CancellationToken] = None
    ) -> Dict[str, Any]:
        """旧版执行逻辑 - 使用 LLM 生成实际结果（支持 Token 取消）"""
        from blueclaw.llm import LLMClient, Message
        from backend.core.task_manager import task_manager
        
        if token:
            token.validate()
        
        task = task_manager.get_task(blueprint.task_id)
        task_context = task.user_input if task else blueprint.task_id
        
        prompt = f"""你正在执行一个任务步骤。
用户原始需求: {task_context}
步骤名称: {step.name}
步骤说明: {step.description}
执行方向: {step.direction}

请根据用户原始需求和步骤信息，生成具体的执行结果。结果应该详细、有信息量，并且与用户原始需求直接相关。
特别注意：用户原始需求中明确提到了地点和主题，请在结果中具体体现该地点的特色景点、活动或信息，不要生成通用内容。
直接输出结果内容，不要添加任何解释。"""
        
        try:
            response = await LLMClient().chat_completion(
                [
                    Message(role="system", content="You are a helpful assistant. Provide detailed, informative results in Chinese."),
                    Message(role="user", content=prompt)
                ]
            )
            if token:
                token.validate()
            result_text = response.content.strip()
            if not result_text or result_text.lower() in ["none", "null", ""]:
                raise StepExecutionError(
                    "empty_response", False,
                    {"message": f"LLM returned empty or null content for step '{step.name}'"}
                )
            return {"success": True, "result": result_text}
        except asyncio.CancelledError:
            raise
        except StepExecutionError:
            raise
        except Exception as e:
            print(f"[Execution] LLM execution failed for {step.name}: {e}")
            raise self._classify_error(e)
    
    async def _execute_step_with_binding(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        token: Optional[CancellationToken] = None
    ) -> Dict[str, Any]:
        """
        Week 20.5: 支持工具绑定的执行（支持 Token 取消）
        
        逻辑：
        1. 检查 step.tool_binding，如果 locked=True 则使用绑定工具
        2. 否则使用 ToolSelector 智能选择
        """
        if token:
            token.validate()
        
        registry = self._get_tool_registry()
        
        # 1. 检查是否有锁定的工具绑定
        if step.tool_binding and step.tool_binding.locked:
            print(f"[Execution] Using bound tool: {step.tool_binding.tool_icon_id}")
            result = await self._execute_with_bound_tool(step, blueprint.task_id, token)
        else:
            # 2. 智能选择工具
            print(f"[Execution] Using smart tool selection")
            result = await self._execute_with_smart_selection(step, blueprint.task_id)
        
        if token:
            token.validate()
        
        # 回填实际执行信息
        if step.tool_binding:
            step.tool_binding.actual_execution = {
                "type": result.get("type"),
                "name": result.get("name"),
                "success": result.get("success")
            }
        
        return result
    
    async def _execute_with_bound_tool(
        self,
        step: ExecutionStep,
        task_id: str,
        token: Optional[CancellationToken] = None
    ) -> Dict[str, Any]:
        """使用绑定的工具执行（支持 Token 取消）"""
        if token:
            token.validate()
        
        registry = self._get_tool_registry()
        if registry:
            try:
                await registry.refresh()
            except Exception as e:
                print(f"[Execution] Tool refresh failed: {e}")
        
        binding = step.tool_binding
        
        if not registry or not binding:
            return {"success": False, "error": "Tool binding not available"}
        
        tool_icon = registry.get(binding.tool_icon_id)
        if not tool_icon:
            return {
                "success": False,
                "error": f"Bound tool not found: {binding.tool_icon_id}"
            }
        
        print(f"[Execution] Using bound tool: {tool_icon.name} ({tool_icon.type.value})")
        
        # 渲染参数模板
        parameters = self._render_parameters(
            tool_icon.config.get("parameters", {}),
            task_id,
            step,
            tool_id=tool_icon.id
        )
        
        # 特殊处理: skill-file 写文档时，用 LLM 生成完整内容
        if binding.tool_icon_id == "skill-file" and parameters.get("operation") == "write":
            from backend.core.task_manager import task_manager
            from blueclaw.llm import LLMClient, Message
            task = task_manager.get_task(task_id)
            task_context = task.user_input if task else task_id
            doc_prompt = f"""请根据以下信息，生成一份完整的、结构化的文档（Markdown格式）。
用户原始需求: {task_context}
步骤名称: {step.name}
步骤说明: {step.description}
执行方向: {step.direction}

要求:
1. 使用 Markdown 格式，包含标题、列表、表格等可视化结构
2. 文档内容必须围绕用户的原始需求展开，提供详细、具体、可操作的信息
3. 如果涉及比较/选择，请给出对比表格和明确推荐
4. 如果涉及价格/预算，请列出具体数字
5. 文档要有清晰的层次结构，方便阅读

直接输出 Markdown 内容，不要添加任何解释。"""
            try:
                if token:
                    token.validate()
                response = await LLMClient().chat_completion(
                    [
                        Message(role="system", content="You are a professional document writer. Output detailed Markdown in Chinese."),
                        Message(role="user", content=doc_prompt)
                    ]
                )
                if token:
                    token.validate()
                parameters["content"] = response.content.strip()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[Execution] LLM doc generation failed: {e}")
                parameters["content"] = parameters.get("content", step.direction)
        
        # 特殊处理: skill-search 查询价格时，构造具体查询词
        if binding.tool_icon_id == "skill-search":
            query = parameters.get("query", step.direction)
            if "杭州" not in query and "价格" not in query:
                query = f"杭州3日游 {step.name} {query}"
            parameters["query"] = query
        
        if token:
            token.validate()
        
        # 执行工具
        try:
            result = await registry.execute_tool(
                tool_id=binding.tool_icon_id,
                context={"task_id": task_id, "step": step},
                parameters=parameters
            )
            if token:
                token.validate()
            return {
                **result,
                "name": tool_icon.name,
                "type": tool_icon.type.value
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "name": tool_icon.name,
                "type": tool_icon.type.value
            }
    
    async def _execute_with_smart_selection(
        self,
        step: ExecutionStep,
        task_id: str
    ) -> Dict[str, Any]:
        """智能选择工具执行"""
        registry = self._get_tool_registry()
        if registry:
            try:
                await registry.refresh()
            except Exception as e:
                print(f"[Execution] Tool refresh failed: {e}")
        selector = self._get_tool_selector()
        
        if not registry:
            return {"success": False, "error": "Tool registry not available"}
        
        # 1. 获取 hint（来自绑定的非锁定工具，或 step.tool_hint）
        hint = None
        if step.tool_binding and not step.tool_binding.locked:
            tool_icon = registry.get(step.tool_binding.tool_icon_id)
            if tool_icon:
                hint = tool_icon.config.get("tool_hint")
        
        if not hint:
            hint = step.tool_hint  # 四要素中的 tool hint
        
        # 2. ToolSelector 智能选择
        if selector:
            selected = await selector.select(
                direction=step.direction,
                hint=hint,
                available_tools=registry.list_all()
            )
            print(f"[Execution] Smart selected: {selected.name} ({selected.type})")
        else:
            # 默认选择第一个可用的 MCP 或 Skill
            tools = registry.list_all()
            selected = None
            for t in tools:
                if t.type.value in ["mcp", "skill"]:
                    from backend.core.tool_selector import ToolSelection
                    selected = ToolSelection(
                        tool_id=t.id,
                        name=t.name,
                        type=t.type.value,
                        confidence=0.5
                    )
                    break
            
            if not selected:
                return {"success": False, "error": "No available tools"}
        
        # 3. 执行选中的工具
        parameters = self._generate_parameters(selected, step, task_id)
        
        try:
            result = await registry.execute_tool(
                tool_id=selected.tool_id,
                context={"task_id": task_id, "step": step},
                parameters=parameters
            )
            return {
                **result,
                "name": selected.name,
                "type": selected.type
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "name": selected.name,
                "type": selected.type
            }
    
    def _render_parameters(
        self,
        parameters,
        task_id: str,
        step: ExecutionStep,
        tool_id: str = ""
    ) -> Dict[str, Any]:
        """渲染参数模板 {{variable}}，支持根据 skill schema 智能映射"""
        rendered = {}
        
        # 收集所有参数名，用于推断缺失参数的默认值
        param_names = set()
        
        # 处理列表类型的参数（如 SkillParameter 列表）
        if isinstance(parameters, list):
            for param in parameters:
                key = None
                schema = {}
                if hasattr(param, 'name'):
                    key = param.name
                    schema = {
                        'type': getattr(param, 'type', 'string'),
                        'default': getattr(param, 'default', None),
                        'required': getattr(param, 'required', True),
                        'description': getattr(param, 'description', ''),
                    }
                elif isinstance(param, dict):
                    key = param.get('name', '')
                    schema = {
                        'type': param.get('type', 'string'),
                        'default': param.get('default', None),
                        'required': param.get('required', True),
                        'description': param.get('description', ''),
                    }
                
                if key:
                    param_names.add(key)
                    rendered[key] = self._resolve_parameter_value(
                        key, schema, step, task_id, tool_id
                    )
            return rendered
        
        # 处理字典类型的参数（通常是 MCP 的 JSON schema properties）
        for key, value in parameters.items():
            param_names.add(key)
            if isinstance(value, dict):
                # JSON schema property
                rendered[key] = self._resolve_parameter_value(
                    key, value, step, task_id, tool_id
                )
            elif isinstance(value, str):
                rendered_value = value
                rendered_value = rendered_value.replace("{{direction}}", step.direction)
                rendered_value = rendered_value.replace("{{task_id}}", task_id)
                rendered_value = rendered_value.replace("{{step_name}}", step.name)
                rendered[key] = rendered_value
            else:
                rendered[key] = value
        return rendered
    
    def _resolve_parameter_value(
        self,
        key: str,
        schema: Dict[str, Any],
        step: ExecutionStep,
        task_id: str,
        tool_id: str
    ) -> Any:
        """根据参数名和上下文解析单个参数的值"""
        direction_lower = step.direction.lower()
        tool_lower = (step.tool or tool_id or "").lower()
        
        # 1. 内容型参数 -> step.direction
        if key in ['code', 'script', 'input', 'query', 'text', 'content', 'command']:
            return step.direction
        
        # 2. operation -> 根据 tool/hint/direction 推断
        if key == 'operation':
            return self._infer_operation(tool_lower, direction_lower)
        
        # 3. path -> 生成跨平台临时路径
        if key == 'path':
            return os.path.join(tempfile.gettempdir(), f"{task_id}_output.txt")
        
        # 4. url -> 如果 direction 像 URL 直接用，否则用 direction 作为搜索词
        if key == 'url':
            if direction_lower.startswith(('http://', 'https://')):
                return step.direction
            return f"https://www.google.com/search?q={step.direction.replace(' ', '+')}"
        
        # 5. variables / context / task_id 等元数据
        if key in ['variables', 'context']:
            return {"task_id": task_id, "step_name": step.name, "direction": step.direction}
        
        # 6. 使用 schema 默认值
        default = schema.get('default')
        if default is not None:
            return default
        
        # 7. 枚举类型 -> 取第一个值
        enum = schema.get('enum')
        if enum:
            return enum[0]
        
        # 8. 根据类型返回空值
        ptype = schema.get('type', 'string')
        if ptype == 'string':
            return ""
        elif ptype == 'integer':
            return 0
        elif ptype == 'number':
            return 0.0
        elif ptype == 'boolean':
            return False
        elif ptype in ('array', 'object'):
            return [] if ptype == 'array' else {}
        
        return ""
    
    def _infer_operation(self, tool_lower: str, direction_lower: str) -> str:
        """根据 tool 名称和任务描述推断 file skill 的 operation"""
        write_hints = ['write', 'save', '创建', '写入', '生成', '保存', '写']
        read_hints = ['read', 'load', '读取', '读取', '读', '加载']
        search_hints = ['search', 'find', '搜索', '查找', '查询']
        delete_hints = ['delete', 'remove', '删除', '移除']
        list_hints = ['list', 'dir', '列举', '列出', '目录']
        
        if any(h in tool_lower for h in write_hints) or any(h in direction_lower for h in write_hints):
            return 'write'
        if any(h in tool_lower for h in read_hints) or any(h in direction_lower for h in read_hints):
            return 'read'
        if any(h in tool_lower for h in search_hints) or any(h in direction_lower for h in search_hints):
            return 'search'
        if any(h in tool_lower for h in delete_hints) or any(h in direction_lower for h in delete_hints):
            return 'delete'
        if any(h in tool_lower for h in list_hints) or any(h in direction_lower for h in list_hints):
            return 'list'
        
        # 默认写操作（常见用例）
        return 'write'
    
    def _generate_parameters(
        self,
        selected: 'ToolSelection',
        step: ExecutionStep,
        task_id: str = ""
    ) -> Dict[str, Any]:
        """为智能选择的工具生成参数，根据具体工具类型和 schema 映射"""
        tool_id = selected.tool_id.lower()
        name = selected.name.lower()
        direction = step.direction
        direction_lower = direction.lower()
        
        # MCP 工具
        if selected.type == "mcp":
            if "search" in name:
                return {"query": direction}
            elif "write" in name or "file" in name:
                return {"path": "/workspace/output.txt", "content": direction}
            elif "read" in name:
                return {"path": "/workspace/output.txt"}
            else:
                return {"input": direction}
        
        # Skill 工具 - 根据 skill ID 智能映射
        if selected.type == "skill":
            if "code" in tool_id or "code" in name:
                return {
                    "code": direction,
                    "variables": {"task_id": task_id or "default", "step_name": step.name}
                }
            elif "file" in tool_id or "file" in name:
                operation = self._infer_operation(tool_id, direction_lower)
                params = {
                    "operation": operation,
                    "path": f"/tmp/{task_id or 'default'}_output.txt"
                }
                if operation in ('write', 'append'):
                    params["content"] = direction
                return params
            elif "shell" in tool_id or "shell" in name:
                return {"command": direction}
            elif "search" in tool_id or "search" in name:
                return {"query": direction}
            elif "browser" in tool_id or "browser" in name:
                if direction_lower.startswith(('http://', 'https://')):
                    return {"url": direction}
                return {"url": f"https://www.google.com/search?q={direction.replace(' ', '+')}"}
            else:
                return {"input": direction}
        
        # Adapter
        if selected.type == "adapter":
            return {"action": direction}
        
        return {}
    
    async def pause_execution(self, blueprint_id: str):
        """暂停执行"""
        self._paused[blueprint_id] = True
        blueprint = self.blueprints.get(blueprint_id)
        if blueprint:
            blueprint.status = StepStatus.PAUSED
    
    async def resume_execution(self, blueprint_id: str):
        """恢复执行"""
        blueprint = self.blueprints.get(blueprint_id)
        if not blueprint or blueprint.status != StepStatus.PAUSED:
            return False
        
        self._paused[blueprint_id] = False
        blueprint.status = StepStatus.RUNNING
        
        # 如果不在运行中，重新启动
        if blueprint_id not in self.running_tasks:
            task = asyncio.create_task(self._execute_blueprint(blueprint_id))
            self.running_tasks[blueprint_id] = task
        
        return True
    
    async def handle_intervention(
        self,
        blueprint_id: str,
        step_id: str,
        action: str,
        data: dict = None
    ) -> Optional[dict]:
        """
        处理用户干预
        action: retry | skip | replan | modify | change_tool
        """
        data = data or {}
        blueprint = self.blueprints.get(blueprint_id)
        if not blueprint:
            return None
        
        step = self._find_step(blueprint, step_id)
        if not step:
            return None
        
        if action == "retry":
            step.status = StepStatus.PENDING
            step.failed_count = 0
            step.error = None
            await self.resume_execution(blueprint_id)
            return {"action": "retry", "step_id": step_id}
        
        elif action == "skip":
            step.status = StepStatus.SKIPPED
            step.result = "用户跳过"
            await self.resume_execution(blueprint_id)
            return {"action": "skip", "step_id": step_id}
        
        elif action == "replan":
            # REPLAN: 从当前步骤重新规划
            custom_input = data.get("custom_input", "")
            new_steps = await self._replan_from_step(blueprint, step_id, custom_input)
            
            await self._notify_replanned(blueprint, step_id, new_steps)
            await self.resume_execution(blueprint_id)
            
            return {
                "action": "replan",
                "from_step_id": step_id,
                "new_steps": [s.to_dict() for s in new_steps]
            }
        
        elif action == "modify":
            if "direction" in data:
                step.direction = data["direction"]
            step.status = StepStatus.PENDING
            await self.resume_execution(blueprint_id)
            return {"action": "modify", "step_id": step_id}
        
        elif action == "change_tool":
            # Week 20.5: 更换工具
            new_tool_id = data.get("tool_id")
            if new_tool_id:
                from backend.tools.models import ToolBinding
                step.tool_binding = ToolBinding(
                    tool_icon_id=new_tool_id,
                    locked=True  # 更换后默认锁定
                )
            # 解锁当前绑定，允许重新选择
            elif step.tool_binding:
                step.tool_binding.locked = False
            
            step.status = StepStatus.PENDING
            step.failed_count = 0
            step.error = None
            await self.resume_execution(blueprint_id)
            return {
                "action": "change_tool",
                "step_id": step_id,
                "tool_id": new_tool_id,
                "locked": step.tool_binding.locked if step.tool_binding else False
            }
        
        return None
    
    async def _replan_from_step(
        self,
        blueprint: ExecutionBlueprint,
        step_id: str,
        user_input: str
    ) -> List[ExecutionStep]:
        """REPLAN核心：从指定步骤重新规划"""
        step = self._find_step(blueprint, step_id)
        if not step:
            return []
        
        # 废弃当前及后续步骤
        for s in self._get_subsequent_steps(blueprint, step):
            s.status = StepStatus.DEPRECATED
        
        # 生成新步骤
        new_steps = []
        for i in range(2):
            new_step = ExecutionStep(
                id=f"step_{uuid.uuid4().hex[:8]}_new",
                name=f"重新规划步骤{i+1}",
                description=f"基于'{user_input}'重新执行",
                direction=f"调整后的执行方向",
                example="预期结果",
                validation="验证规则",
                tool="Skill",
                dependencies=[step_id if i == 0 else new_steps[i-1].id],
                position={"x": 100 + (len(blueprint.steps) + i) * 250, "y": 500}
            )
            new_steps.append(new_step)
            blueprint.steps.append(new_step)
        
        self._resolve_dependencies(blueprint.steps)
        return new_steps
    
    # ========== 通知方法 ==========
    
    async def _notify_step_started(self, blueprint: ExecutionBlueprint, step: ExecutionStep):
        """通知步骤开始 - 使用 state_sync"""
        from blueclaw.core.state_sync import state_sync
        await state_sync.push_execution_step_started(blueprint.task_id, step)
    
    async def _notify_step_completed(self, blueprint: ExecutionBlueprint, step: ExecutionStep):
        """通知步骤完成 - 使用 state_sync"""
        from blueclaw.core.state_sync import state_sync
        await state_sync.push_execution_step_completed(blueprint.task_id, step)
    
    async def _notify_step_failed(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None
    ):
        """通知步骤失败 - 使用 state_sync"""
        from blueclaw.core.state_sync import state_sync
        await state_sync.push_execution_step_failed(
            blueprint.task_id, step, error_type=error_type, stack_trace=stack_trace
        )
    
    async def _notify_intervention_needed(self, blueprint: ExecutionBlueprint, step: ExecutionStep):
        """通知需要干预"""
        from blueclaw.core.state_sync import state_sync
        await state_sync.push_execution_intervention_needed(blueprint.task_id, step, blueprint)
    
    async def _notify_replanned(self, blueprint: ExecutionBlueprint, from_step_id: str, new_steps: List[ExecutionStep]):
        """通知REPLAN结果"""
        from blueclaw.core.state_sync import state_sync
        await state_sync.push_execution_replanned(blueprint.task_id, from_step_id, [], new_steps)
    
    async def _sync_all_step_states(self, blueprint: ExecutionBlueprint, steps: list):
        """同步所有步骤状态到前端（确保最终一致性）"""
        for step in steps:
            try:
                if step.status == StepStatus.COMPLETED:
                    await self._notify_step_completed(blueprint, step)
                elif step.status == StepStatus.FAILED:
                    await self._notify_step_failed(blueprint, step)
                elif step.status == StepStatus.RUNNING:
                    # 如果还在running，可能是通知丢失，重新通知
                    await self._notify_step_started(blueprint, step)
                await asyncio.sleep(0.05)  # 小延迟避免消息拥塞
            except Exception as e:
                print(f"[Execution] Failed to sync step {step.id}: {e}")
    
    async def _notify_completed(self, blueprint: ExecutionBlueprint):
        """通知执行完成"""
        from blueclaw.core.state_sync import state_sync
        import time
        execution_time = time.time() - (blueprint.started_at and datetime.fromisoformat(blueprint.started_at).timestamp() or time.time())
        await state_sync.push_execution_completed(blueprint.task_id, blueprint, execution_time)
    
    # ========== 辅助方法 ==========
    
    def _check_dependencies_satisfied(self, blueprint: ExecutionBlueprint, step: ExecutionStep) -> bool:
        for dep_id in step.dependencies:
            dep_step = self._find_step(blueprint, dep_id)
            if not dep_step or dep_step.status not in [StepStatus.COMPLETED, StepStatus.SKIPPED]:
                return False
        return True
    
    async def _wait_for_dependencies(self, blueprint: ExecutionBlueprint, step: ExecutionStep):
        while not self._check_dependencies_satisfied(blueprint, step):
            await asyncio.sleep(0.1)
    
    async def _wait_for_dependencies_with_token(
        self,
        blueprint: ExecutionBlueprint,
        step: ExecutionStep,
        token: Optional[CancellationToken] = None
    ):
        """等待依赖完成，同时检查 Token 取消状态"""
        while not self._check_dependencies_satisfied(blueprint, step):
            if token and token.is_cancelled:
                raise asyncio.CancelledError(f"Dependencies wait cancelled for step {step.name}")
            await asyncio.sleep(0.1)
    
    def _find_step(self, blueprint: ExecutionBlueprint, step_id: str) -> Optional[ExecutionStep]:
        for step in blueprint.steps:
            if step.id == step_id:
                return step
        return None
    
    def _get_subsequent_steps(self, blueprint: ExecutionBlueprint, step: ExecutionStep) -> List[ExecutionStep]:
        """获取指定步骤之后的所有步骤"""
        subsequent = []
        found = False
        for s in blueprint.steps:
            if found and s.status != StepStatus.DEPRECATED:
                subsequent.append(s)
            if s.id == step.id:
                found = True
        return subsequent
    
    def _resolve_dependencies(self, steps: List[ExecutionStep]):
        """解析依赖关系"""
        # 如果 LLM 已经生成了自定义依赖关系（至少一个步骤有非空依赖），
        # 则保留原样，不破坏可能存在的并行分支结构
        has_custom_deps = any(s.dependencies for s in steps)
        if has_custom_deps:
            return
        
        for i, step in enumerate(steps):
            if i > 0 and not step.dependencies:
                # 默认依赖前一个非废弃步骤
                for j in range(i-1, -1, -1):
                    if steps[j].status != StepStatus.DEPRECATED:
                        step.dependencies = [steps[j].id]
                        break
    
    def _compute_branch_layout(self, steps: List[ExecutionStep]):
        """计算 DAG 分支布局，标记主路径和汇合节点"""
        if not steps:
            return
        
        id_to_step = {s.id: s for s in steps}
        
        # 构建图和入度
        adj = {s.id: [] for s in steps}
        in_degree = {s.id: 0 for s in steps}
        for s in steps:
            for dep_id in s.dependencies:
                if dep_id in id_to_step:
                    adj[dep_id].append(s.id)
                    in_degree[s.id] += 1
        
        # 拓扑排序计算层级
        from collections import deque
        q = deque([sid for sid, deg in in_degree.items() if deg == 0])
        level = {sid: 0 for sid in id_to_step}
        while q:
            u = q.popleft()
            for v in adj[u]:
                level[v] = max(level[v], level[u] + 1)
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    q.append(v)
        
        # 找最长路径（主路径）- 动态规划
        # dp[sid] = 从起点到 sid 的最长路径长度
        topo_order = sorted(steps, key=lambda s: level[s.id])
        dp = {s.id: 0 for s in steps}
        prev = {s.id: None for s in steps}
        for s in topo_order:
            sid = s.id
            for dep_id in s.dependencies:
                if dep_id in dp and dp[dep_id] + 1 > dp[sid]:
                    dp[sid] = dp[dep_id] + 1
                    prev[sid] = dep_id
        
        # 找到终点最长的节点
        end_node = max(steps, key=lambda s: dp[s.id]).id
        main_path_ids = set()
        cur = end_node
        while cur is not None:
            main_path_ids.add(cur)
            cur = prev[cur]
        
        # 标记主路径
        for s in steps:
            s.is_main_path = s.id in main_path_ids
        
        # 识别汇合节点：入度 > 1 且至少一个依赖不是主路径
        for s in steps:
            if len(s.dependencies) > 1:
                has_branch_input = any(dep not in main_path_ids for dep in s.dependencies)
                if has_branch_input:
                    s.is_convergence = True
                    s.convergence_type = 'parallel'
        
        # 分支节点布局
        # x 按层级，y 按主路径/分支分配
        X_SPACING = 260
        Y_MAIN = 400
        Y_OFFSET = 130
        
        # 统计每个主路径节点分出的分支数量
        branch_count_by_main = {}
        for s in steps:
            if not s.is_main_path:
                # 找到它的主路径前置依赖
                main_predecessors = [dep for dep in s.dependencies if dep in main_path_ids]
                if main_predecessors:
                    anchor = main_predecessors[0]
                    branch_count_by_main[anchor] = branch_count_by_main.get(anchor, 0) + 1
        
        branch_index_by_main = {}
        for s in steps:
            if s.is_main_path:
                s.position = {"x": 100 + level[s.id] * X_SPACING, "y": Y_MAIN}
            else:
                main_predecessors = [dep for dep in s.dependencies if dep in main_path_ids]
                if main_predecessors:
                    anchor = main_predecessors[0]
                    idx = branch_index_by_main.get(anchor, 0) + 1
                    branch_index_by_main[anchor] = idx
                    # 上下交替：奇数向下，偶数向上
                    direction = 1 if idx % 2 == 1 else -1
                    y_offset = Y_OFFSET * ((idx + 1) // 2)
                    s.position = {"x": 100 + level[s.id] * X_SPACING, "y": Y_MAIN + direction * y_offset}
                else:
                    # 独立分支，也计算偏移
                    s.position = {"x": 100 + level[s.id] * X_SPACING, "y": Y_MAIN + Y_OFFSET}
        
        print(f"[BranchLayout] Main path: {sorted(list(main_path_ids))}")
        print(f"[BranchLayout] Convergence nodes: {[s.id for s in steps if s.is_convergence]}")
    
    def _create_default_steps(self, thinking_path: List[dict]) -> List[dict]:
        return [
            {"name": "准备环境", "description": "准备执行环境", "direction": "环境准备", "example": "准备完成", "validation": "检查通过", "tool": "Skill"},
            {"name": "执行主要任务", "description": "执行核心任务", "direction": "任务执行", "example": "任务完成", "validation": "结果符合预期", "tool": "Skill"}
        ]


# Global instance
execution_engine = ExecutionEngine()
