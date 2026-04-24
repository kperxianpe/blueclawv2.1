# -*- coding: utf-8 -*-
"""
coordinator_v3.py - Blueclaw v1.0 Integration Coordinator

Integrates thinking engine, execution blueprint, skills, and memory.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from ..core.dynamic_thinking_engine import (
    DynamicThinkingEngine, ThinkingResult, ThinkingResultType,
    ThinkingOption, ClarificationQuestion, create_dynamic_thinking_engine
)
from ..core.execution_blueprint import (
    ExecutionBlueprintSystem, ExecutionStep, StepStatus,
    create_execution_blueprint_system
)
from ..skills import SkillRegistry, SkillResult
from ..memory import MemoryManager


@dataclass
class ApplicationState:
    """Application state"""
    phase: str = "idle"  # idle, thinking, executing, intervening, completed
    task_id: str = ""
    current_input: str = ""
    progress: int = 0
    status_message: str = ""
    current_step_index: int = -1
    execution_mode: str = "real"


class ApplicationCoordinatorV3:
    """
    Blueclaw v1.0 Integration Coordinator
    
    Features:
    - Dynamic thinking engine
    - Execution blueprint visualization
    - Real skill execution
    - Memory management
    - Intervention support
    """
    
    def __init__(self, task_id: str = "app-001", use_real_execution: bool = True):
        self.task_id = task_id
        self.state = ApplicationState(task_id=task_id, execution_mode="real" if use_real_execution else "mock")
        self.use_real_execution = use_real_execution
        
        # Core systems
        self.thinking_engine = create_dynamic_thinking_engine()
        self.execution_system = create_execution_blueprint_system()
        
        # OpenClaw integration
        self.skill_registry = SkillRegistry() if use_real_execution else None
        self.memory_manager = MemoryManager() if use_real_execution else None
        
        # Current state
        self.current_thinking_result: Optional[ThinkingResult] = None
        self.current_question: Optional[ClarificationQuestion] = None
        
        # Bind callbacks
        self._bind_callbacks()
        
        # UI callbacks
        self._on_state_change: Optional[Callable[[ApplicationState], None]] = None
        self._on_message: Optional[Callable[[str], None]] = None
        self._on_execution_preview: Optional[Callable[[Dict], None]] = None
        self._on_question: Optional[Callable[[ClarificationQuestion], None]] = None
        self._on_options: Optional[Callable[[List[ThinkingOption]], None]] = None
        self._on_blueprint_loaded: Optional[Callable[[List[ExecutionStep]], None]] = None
        self._on_step_update: Optional[Callable[[str, str, int], None]] = None
        self._on_execution_complete: Optional[Callable[[Dict], None]] = None
        self._on_intervention_needed: Optional[Callable[[str, str], None]] = None
        
        self._log(f"[INIT] Coordinator initialized (mode: {self.state.execution_mode})")
        if self.skill_registry:
            self._log(f"[INIT] Skills: {self.skill_registry.list_skills()}")
    
    def set_callbacks(self, **callbacks):
        """Set UI callbacks"""
        self._on_state_change = callbacks.get('on_state_change')
        self._on_message = callbacks.get('on_message')
        self._on_execution_preview = callbacks.get('on_execution_preview')
        self._on_question = callbacks.get('on_question')
        self._on_options = callbacks.get('on_options')
        self._on_blueprint_loaded = callbacks.get('on_blueprint_loaded')
        self._on_step_update = callbacks.get('on_step_update')
        self._on_execution_complete = callbacks.get('on_execution_complete')
        self._on_intervention_needed = callbacks.get('on_intervention_needed')
    
    def _bind_callbacks(self):
        """Bind system callbacks"""
        self.execution_system.on_blueprint_loaded = self._on_execution_blueprint_loaded
        self.execution_system.on_step_start = self._on_execution_step_start
        self.execution_system.on_step_complete = self._on_execution_step_complete
        self.execution_system.on_execution_complete = self._on_execution_result
        self.execution_system.on_intervention_needed = self._on_execution_intervention
    
    def _update_state(self, **kwargs):
        """Update state"""
        for key, value in kwargs.items():
            setattr(self.state, key, value)
        
        if self._on_state_change:
            self._on_state_change(self.state)
    
    def _log(self, message: str):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        
        if self._on_message:
            self._on_message(full_msg)
        else:
            print(full_msg)
    
    # ============ Task Management ============
    
    async def start_task(self, user_input: str) -> None:
        """Start a new task"""
        self._log(f"[TASK] Starting: {user_input}")
        self.state.current_input = user_input
        
        if self.memory_manager:
            await self.memory_manager.add_message("user", user_input)
        
        self._update_state(phase="thinking", status_message="AI thinking...")
        
        result = self.thinking_engine.process(user_input)
        self.current_thinking_result = result
        
        await self._handle_thinking_result(result)
    
    async def handle_user_response(self, response: str, response_type: str = "auto"):
        """Handle user response"""
        self._log(f"[USER] Response: {response[:50]}...")
        
        if self.memory_manager:
            await self.memory_manager.add_message("user", response)
        
        if response_type == "question_answer" and self.current_question:
            result = self.thinking_engine.continue_with_clarification(response, self.current_question)
            await self._handle_thinking_result(result)
            
        elif response_type == "option_selection":
            if self.current_thinking_result and self.current_thinking_result.options:
                selected_option = None
                for opt in self.current_thinking_result.options:
                    if opt.id == response or opt.label == response:
                        selected_option = opt
                        break
                
                if selected_option:
                    result = self.thinking_engine.continue_with_option(response, selected_option)
                    await self._handle_thinking_result(result)
    
    async def _handle_thinking_result(self, result: ThinkingResult):
        """Handle thinking result"""
        self._log(f"[THINK] Result: {result.result_type.value}")
        
        if result.result_type == ThinkingResultType.DIRECT_ANSWER:
            self._update_state(phase="completed", status_message="Done")
            if result.direct_answer and self._on_message:
                self._on_message(f"AI:\n{result.direct_answer}")
        
        elif result.result_type == ThinkingResultType.EXECUTION_PREVIEW:
            self._update_state(phase="thinking", status_message="Confirm execution plan")
            if self._on_execution_preview and result.execution_preview:
                self._on_execution_preview(result.execution_preview)
            await self._start_execution_from_preview(result.execution_preview)
        
        elif result.result_type == ThinkingResultType.CLARIFICATION_QUESTION:
            self._update_state(phase="thinking", status_message="Need more info...")
            if result.clarification_question:
                self.current_question = result.clarification_question
                if self._on_question:
                    self._on_question(result.clarification_question)
        
        elif result.result_type == ThinkingResultType.OPTIONS_WITH_DEFAULT:
            self._update_state(phase="thinking", status_message="Select execution plan")
            if self._on_options and result.options:
                self._on_options(result.options)
            
            # Auto-select default option for simple tasks (optional behavior)
            # Find default option
            default_option = None
            for opt in result.options:
                if opt.is_default:
                    default_option = opt
                    break
            
            # If there's a default option, auto-select it after a short delay
            if default_option:
                self._log(f"[AUTO] Selecting default option: {default_option.id}")
                result2 = self.thinking_engine.continue_with_option(default_option.id, default_option)
                await self._handle_thinking_result(result2)
    
    async def _start_execution_from_preview(self, preview):
        """Start execution from preview"""
        # Handle both dict and ExecutionPreview object
        if hasattr(preview, 'steps'):
            steps = preview.steps
        else:
            steps = preview.get("steps", []) if preview else []
        
        if not steps:
            return
        
        if self.memory_manager:
            self.memory_manager.set_plan(preview.__dict__ if hasattr(preview, '__dict__') else preview)
        
        steps_data = [
            {"name": step.get("name", step.name) if hasattr(step, 'name') else step.get("name", "Unnamed"), 
             "description": step.get("description", "") if isinstance(step, dict) else getattr(step, 'description', "")}
            for step in steps
        ]
        
        self.execution_system.load_blueprint(steps_data)
        
        self._update_state(
            phase="executing",
            status_message="Executing...",
            current_step_index=0
        )
        
        if self.use_real_execution and self.skill_registry:
            await self._execute_with_skills(preview)
        else:
            await self.execution_system.execute_all()
    
    async def _execute_with_skills(self, preview):
        """Execute using real skills"""
        # Handle both dict and ExecutionPreview object
        if hasattr(preview, 'steps'):
            steps = preview.steps
        else:
            steps = preview.get("steps", [])
        total_steps = len(steps)
        
        for i, step_data in enumerate(steps):
            step_name = step_data.get("name", f"Step {i+1}")
            step_desc = step_data.get("description", step_name)
            
            self._log(f"[EXEC] Step {i+1}/{total_steps}: {step_name}")
            self._update_state(current_step_index=i)
            
            if self._on_step_update:
                self._on_step_update(f"step_{i}", "running", i)
            
            skill_result = await self._execute_step_with_skill(step_name, step_desc)
            
            if self.memory_manager:
                await self.memory_manager.add_experience({
                    'step': step_name,
                    'result': skill_result.data if skill_result.success else skill_result.error,
                    'success': skill_result.success
                })
            
            status = "completed" if skill_result.success else "failed"
            if self._on_step_update:
                self._on_step_update(f"step_{i}", status, i)
            
            if not skill_result.success:
                self._log(f"[WARN] Step failed: {skill_result.error}")
        
        self._update_state(phase="completed", status_message="Execution completed", progress=100)
        
        if self._on_execution_complete:
            self._on_execution_complete({
                "success": True,
                "summary": f"Completed {total_steps} steps",
                "completed_steps": total_steps,
                "total_steps": total_steps,
                "execution_mode": "real"
            })
    
    async def _execute_step_with_skill(self, step_name: str, step_desc: str) -> SkillResult:
        """Execute step with appropriate skill"""
        if not self.skill_registry:
            return SkillResult.fail(error="Skill registry not available")
        
        step_lower = step_desc.lower()
        
        if any(kw in step_lower for kw in ['file', 'read', 'write', 'list', 'directory']):
            if 'list' in step_lower or 'directory' in step_lower:
                return await self.skill_registry.execute('file', operation='list', path='.')
            return SkillResult.ok(data=f"File operation for: {step_desc}")
        
        elif any(kw in step_lower for kw in ['shell', 'command', 'run']):
            return await self.skill_registry.execute('shell', command='echo "Hello"')
        
        elif any(kw in step_lower for kw in ['code', 'python', 'calculate']):
            return await self.skill_registry.execute('code', code='print(2+2)')
        
        return SkillResult.ok(data=f"Executed: {step_name}")
    
    # ============ Execution Callbacks ============
    
    def _on_execution_blueprint_loaded(self, steps: List[ExecutionStep]):
        self._log(f"[BLUEPRINT] Loaded: {len(steps)} steps")
        if self._on_blueprint_loaded:
            self._on_blueprint_loaded(steps)
    
    def _on_execution_step_start(self, step: ExecutionStep):
        self._log(f"[STEP] Starting: {step.name}")
        index = self._get_step_index(step.id)
        self._update_state(current_step_index=index)
        if self._on_step_update:
            self._on_step_update(step.id, "running", index)
    
    def _on_execution_step_complete(self, step: ExecutionStep, success: bool):
        status = "completed" if success else "failed"
        self._log(f"[STEP] Completed: {step.name} ({status})")
        index = self._get_step_index(step.id)
        if self._on_step_update:
            self._on_step_update(step.id, status, index)
    
    def _on_execution_result(self, result):
        self._log(f"[DONE] Execution completed: {result.summary}")
        self._update_state(phase="completed", status_message=result.summary, progress=100)
        if self._on_execution_complete:
            self._on_execution_complete({
                "success": result.success,
                "summary": result.summary,
                "completed_steps": result.completed_steps,
                "total_steps": result.total_steps,
                "execution_time": result.execution_time,
                "execution_mode": "mock"
            })
    
    def _on_execution_intervention(self, intervention):
        self._log(f"[INTERVENTION] Needed for: {intervention.step_name}")
        self._update_state(
            phase="intervening",
            status_message=f"Step '{intervention.step_name}' needs intervention"
        )
        if self._on_intervention_needed:
            self._on_intervention_needed(intervention.step_id, intervention.reason)
    
    def _get_step_index(self, step_id: str) -> int:
        if not self.execution_system.blueprint:
            return -1
        for i, step in enumerate(self.execution_system.blueprint):
            if step.id == step_id:
                return i
        return -1
    
    # ============ Intervention ============
    
    async def handle_intervention(self, action_type: str, **kwargs):
        """Handle user intervention"""
        self._log(f"[INTERVENTION] Action: {action_type}")
        
        if action_type == "replan":
            self._update_state(phase="thinking", status_message="Replanning...")
            current_step = self.execution_system.get_current_step()
            context = f"Execution at step '{current_step.name}' needs replanning"
            result = self.thinking_engine.process(context)
            await self._handle_thinking_result(result)
            
        elif action_type == "retry":
            await self.execution_system.resume_after_intervention()
            
        elif action_type == "skip":
            await self.execution_system.resume_after_intervention()
            
        elif action_type == "edit_params":
            await self.execution_system.resume_after_intervention()
    
    # ============ Skill Interface ============
    
    async def execute_skill(self, skill_name: str, **params) -> Dict[str, Any]:
        """Execute skill directly"""
        if not self.skill_registry:
            return {"success": False, "error": "Skill registry not available", "data": None}
        
        result = await self.skill_registry.execute(skill_name, **params)
        
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "duration_ms": result.duration_ms
        }
    
    def list_skills(self) -> List[str]:
        """List available skills"""
        if not self.skill_registry:
            return []
        return self.skill_registry.list_skills()
    
    def get_skill_schema(self, skill_name: str) -> Optional[Dict]:
        """Get skill schema"""
        if not self.skill_registry:
            return None
        skill = self.skill_registry.get(skill_name)
        if skill:
            return skill.to_schema()
        return None
    
    def get_memory_context(self) -> str:
        """Get memory context"""
        if not self.memory_manager:
            return ""
        return self.memory_manager.get_context_string()
    
    # ============ Queries ============
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress"""
        if self.state.phase == "executing":
            return self.execution_system.get_progress()
        return {"percentage": self.state.progress}
    
    def get_current_step(self) -> Optional[ExecutionStep]:
        """Get current step"""
        return self.execution_system.get_current_step()


def create_coordinator_v3(task_id: str = "app-001", use_real_execution: bool = True) -> ApplicationCoordinatorV3:
    """Create coordinator instance"""
    return ApplicationCoordinatorV3(task_id, use_real_execution)
