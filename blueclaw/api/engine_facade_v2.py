#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw Engine Facade V2 - Week 19 Integration

Bridges Week 15-18 EngineFacade with Week 19 ThinkingEngine and ExecutionEngine.
Provides a unified interface while using the new engine components.
"""

import asyncio
from typing import List, Dict, Optional, Callable, Any
from dataclasses import asdict

from blueclaw.core.thinking_engine import thinking_engine, ThinkingNode
from blueclaw.core.execution_engine import execution_engine, ExecutionBlueprint, StepStatus
from blueclaw.core.state_sync import state_sync
from backend.models.task import Task, TaskStatus
from backend.core.task_manager import task_manager

# Legacy imports for compatibility
from blueclaw.core.intent_analyzer import IntentAnalyzer, IntentType, IntentAnalysis
from blueclaw.core.confidence_scorer import ConfidenceScorer


class BlueclawEngineFacadeV2:
    """
    Engine Facade V2 - Integrates Week 19 engines with legacy interface
    
    Features:
    - Uses Week 19 ThinkingEngine for 3-layer convergence
    - Uses Week 19 ExecutionEngine for pause/resume/REPLAN
    - Maintains backward compatibility with V1 interface
    - Integrates with TaskManager and Checkpoint system
    """
    
    def __init__(self, session_id: str, persistence_path: str = "./sessions"):
        self.session_id = session_id
        self.persistence_path = persistence_path
        
        # Legacy components (for compatibility)
        self.intent_analyzer = IntentAnalyzer()
        self.confidence_scorer = ConfidenceScorer()
        
        # Week 19 engines
        self.thinking_engine = thinking_engine
        self.execution_engine = execution_engine
        self.state_sync = state_sync
        
        # State
        self.current_task_id: Optional[str] = None
        self.current_blueprint_id: Optional[str] = None
        
        # Callbacks for WebSocket layer
        self.callbacks: Dict[str, Callable] = {}
    
    def set_callbacks(self, **callbacks):
        """Set callbacks for WebSocket notifications"""
        self.callbacks = callbacks
        # Set up state sync to use callbacks
        if callbacks.get('broadcast'):
            # Create a wrapper server that uses the callback
            class CallbackServer:
                def __init__(self, broadcast_callback):
                    self.broadcast_callback = broadcast_callback
                
                async def broadcast_to_task(self, task_id: str, message: dict):
                    await self.broadcast_callback(task_id, message)
            
            state_sync.set_websocket_server(CallbackServer(callbacks['broadcast']))
    
    # ========== Thinking Phase ==========
    
    async def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input - creates task and starts thinking
        
        Returns:
            {"type": "thinking_node", "node": {...}, "task_id": ...}
        """
        # Create task via TaskManager
        task = await task_manager.create_task(user_input)
        self.current_task_id = task.id
        
        # Start thinking with Week 19 engine
        root_node = await self.thinking_engine.start_thinking(task.id, user_input)
        
        # Update task status
        await task_manager.update_task_status(task.id, TaskStatus.THINKING)
        
        # Broadcast via state sync
        await self.state_sync.push_thinking_node_created(task.id, root_node, is_root=True)
        
        return {
            "type": "thinking_node",
            "node": root_node.to_dict(),
            "task_id": task.id,
            "session_id": self.session_id
        }
    
    async def select_option(self, task_id: str, node_id: str, option_id: str) -> Dict[str, Any]:
        """
        User selects an option (A/B/C)
        
        Returns:
            {"type": "thinking_node", "node": {...}} or
            {"type": "blueprint_ready", "steps": [...]}
        """
        result = await self.thinking_engine.select_option(task_id, node_id, option_id)
        
        if result.get("has_more_options"):
            # Continue thinking
            next_node = result.get("next_node")
            await self.state_sync.push_thinking_node_created(task_id, next_node, is_root=False)
            
            return {
                "type": "thinking_node",
                "node": next_node.to_dict(),
                "task_id": task_id,
                "session_id": self.session_id
            }
        else:
            # Converged - ready for execution
            final_path = result.get("final_path", [])
            await self.state_sync.push_thinking_completed(task_id, final_path)
            
            return {
                "type": "blueprint_ready",
                "final_path": final_path,
                "task_id": task_id,
                "session_id": self.session_id
            }
    
    async def select_custom_input(self, task_id: str, node_id: str, custom_input: str) -> Dict[str, Any]:
        """
        User provides custom input (4th white block)
        
        Returns:
            {"type": "thinking_node", ...} or {"type": "blueprint_ready", ...}
        """
        result = await self.thinking_engine.select_custom_input(task_id, node_id, custom_input)
        
        if result.get("has_more_options"):
            next_node = result.get("next_node")
            await self.state_sync.push_thinking_node_created(task_id, next_node, is_root=False)
            
            return {
                "type": "thinking_node",
                "node": next_node.to_dict(),
                "task_id": task_id,
                "session_id": self.session_id
            }
        else:
            final_path = result.get("final_path", [])
            await self.state_sync.push_thinking_completed(task_id, final_path)
            
            return {
                "type": "blueprint_ready",
                "final_path": final_path,
                "task_id": task_id,
                "session_id": self.session_id
            }
    
    async def confirm_execution(self, task_id: str) -> Dict[str, Any]:
        """
        Confirm thinking and generate execution blueprint
        
        Returns:
            {"type": "blueprint_loaded", "blueprint": {...}}
        """
        # Get final path
        final_path = self.thinking_engine.get_final_path(task_id)
        
        # Update task status
        await task_manager.update_task_status(task_id, TaskStatus.EXECUTING)
        
        # Generate blueprint
        blueprint = await self.execution_engine.create_blueprint(task_id, final_path)
        self.current_blueprint_id = blueprint.id
        
        # Update task with blueprint
        task = task_manager.get_task(task_id)
        if task:
            task.execution_blueprint = blueprint.to_dict()
        
        # Broadcast
        await self.state_sync.push_execution_blueprint_loaded(task_id, blueprint)
        
        return {
            "type": "blueprint_loaded",
            "blueprint": blueprint.to_dict(),
            "blueprint_id": blueprint.id,
            "task_id": task_id,
            "session_id": self.session_id
        }
    
    # ========== Execution Phase ==========
    
    async def execute_blueprint(self, blueprint_id: str = None) -> Dict[str, Any]:
        """
        Execute blueprint
        
        Returns:
            {"status": "started", "blueprint_id": ...}
        """
        bp_id = blueprint_id or self.current_blueprint_id
        if not bp_id:
            return {"status": "error", "error": "No blueprint to execute"}
        
        success = await self.execution_engine.start_execution(bp_id)
        
        if success:
            self._notify('on_execution_started', {
                "session_id": self.session_id,
                "blueprint_id": bp_id
            })
            return {"status": "started", "blueprint_id": bp_id, "session_id": self.session_id}
        else:
            return {"status": "error", "error": "Failed to start execution"}
    
    async def pause_execution(self, blueprint_id: str = None) -> Dict[str, Any]:
        """Pause execution"""
        bp_id = blueprint_id or self.current_blueprint_id
        if not bp_id:
            return {"status": "error", "error": "No blueprint"}
        
        await self.execution_engine.pause_execution(bp_id)
        
        # Get task_id from blueprint
        blueprint = self.execution_engine.blueprints.get(bp_id)
        if blueprint:
            await self.state_sync.push_execution_paused(blueprint.task_id, bp_id)
        
        return {"status": "paused", "blueprint_id": bp_id}
    
    async def resume_execution(self, blueprint_id: str = None) -> Dict[str, Any]:
        """Resume execution"""
        bp_id = blueprint_id or self.current_blueprint_id
        if not bp_id:
            return {"status": "error", "error": "No blueprint"}
        
        success = await self.execution_engine.resume_execution(bp_id)
        
        if success:
            blueprint = self.execution_engine.blueprints.get(bp_id)
            if blueprint:
                await self.state_sync.push_execution_resumed(blueprint.task_id, bp_id)
            return {"status": "resumed", "blueprint_id": bp_id}
        else:
            return {"status": "error", "error": "Not in paused state"}
    
    # ========== Intervention Phase ==========
    
    async def intervene(
        self,
        blueprint_id: str,
        step_id: str,
        action_type: str,
        custom_input: str = None
    ) -> Dict[str, Any]:
        """
        Handle intervention
        
        Actions:
        - replan: Trigger REPLAN from step
        - skip: Skip current step
        - retry: Retry execution
        - modify: Modify step direction
        """
        intervention_data = {}
        if custom_input:
            intervention_data["custom_input"] = custom_input
        
        result = await self.execution_engine.handle_intervention(
            blueprint_id=blueprint_id,
            step_id=step_id,
            action=action_type,
            data=intervention_data
        )
        
        if not result:
            return {"status": "error", "error": "Intervention failed"}
        
        # Broadcast REPLAN if applicable
        if action_type == "replan":
            blueprint = self.execution_engine.blueprints.get(blueprint_id)
            if blueprint:
                new_steps = result.get("new_steps", [])
                await self.state_sync.push_execution_replanned(
                    blueprint.task_id,
                    step_id,
                    [],  # abandoned steps
                    new_steps
                )
        
        return {
            "type": "intervention_result",
            "action": action_type,
            "result": result,
            "blueprint_id": blueprint_id,
            "session_id": self.session_id
        }
    
    def get_intervention_actions(self, step_id: str) -> List[Dict[str, str]]:
        """Get available intervention actions for a failed step"""
        return [
            {"id": "replan", "label": "重新规划", "description": "更换策略重新执行"},
            {"id": "skip", "label": "跳过此步", "description": "继续后续步骤"},
            {"id": "retry", "label": "重试", "description": "再次尝试执行"},
            {"id": "modify", "label": "修改方案", "description": "调整执行方向"}
        ]
    
    # ========== Status Queries ==========
    
    def get_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        if not self.current_blueprint_id:
            return {
                "session_id": self.session_id,
                "phase": "idle",
                "progress": 0
            }
        
        blueprint = self.execution_engine.blueprints.get(self.current_blueprint_id)
        if not blueprint:
            return {"session_id": self.session_id, "phase": "unknown"}
        
        total = len(blueprint.steps)
        completed = sum(1 for s in blueprint.steps if s.status == StepStatus.COMPLETED)
        
        return {
            "session_id": self.session_id,
            "phase": blueprint.status.value,
            "blueprint_id": blueprint.id,
            "task_id": blueprint.task_id,
            "total_steps": total,
            "completed_steps": completed,
            "progress": (completed / total * 100) if total > 0 else 0
        }
    
    def get_thinking_chain(self, task_id: str = None) -> Dict[str, Any]:
        """Get thinking chain data"""
        tid = task_id or self.current_task_id
        if not tid:
            return {"session_id": self.session_id, "nodes": []}
        
        path = self.thinking_engine.get_final_path(tid)
        
        return {
            "session_id": self.session_id,
            "task_id": tid,
            "nodes": path,
            "converged": len(path) >= 2
        }
    
    # ========== Utility Methods ==========
    
    def _notify(self, event: str, data: Dict):
        """Send notification via callback"""
        callback = self.callbacks.get(event)
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                print(f"Callback error for {event}: {e}")
    
    async def load_task(self, task_id: str) -> bool:
        """Load existing task"""
        task = task_manager.get_task(task_id)
        if task:
            self.current_task_id = task_id
            if task.execution_blueprint:
                self.current_blueprint_id = task.execution_blueprint.get("id")
            return True
        return False


# Factory function for creating the appropriate facade
def create_facade(session_id: str, use_v2: bool = True, **kwargs) -> Any:
    """
    Create EngineFacade instance
    
    Args:
        session_id: Unique session ID
        use_v2: If True, use Week 19 engines; if False, use legacy engines
        **kwargs: Additional arguments passed to facade
    
    Returns:
        EngineFacade instance
    """
    if use_v2:
        return BlueclawEngineFacadeV2(session_id, **kwargs)
    else:
        from blueclaw.api.engine_facade import BlueclawEngineFacade
        return BlueclawEngineFacade(session_id, **kwargs)
