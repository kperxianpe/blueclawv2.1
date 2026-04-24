#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueclaw Engine Facade

Integrates all 10 core features from Week 16 and provides a unified interface.
Connects with WebSocket layer from Week 15.5.
"""

import asyncio
from typing import List, Dict, Optional, Callable, Any
from dataclasses import asdict

from blueclaw.core.intent_analyzer import IntentAnalyzer, IntentType, IntentAnalysis
from blueclaw.core.confidence_scorer import ConfidenceScorer
from blueclaw.core.option_generator import OptionGenerator
from blueclaw.core.thinking_chain import ThinkingChain
from blueclaw.core.blueprint_generator import BlueprintGenerator, ExecutionStep, StepStatus
from blueclaw.core.step_executor import StepExecutor
from blueclaw.core.dependency_checker import DependencyChecker
from blueclaw.core.intervention_trigger import InterventionTrigger
from blueclaw.core.replan_engine import ReplanEngine
from blueclaw.core.state_persistence import StatePersistence


class BlueclawEngineFacade:
    """
    Blueclaw Engine Facade
    
    Integrates all feature modules and provides a unified interface for:
    - Thinking phase: process user input, generate options
    - Execution phase: execute blueprint steps
    - Intervention phase: handle failures and replan
    """
    
    def __init__(self, session_id: str, persistence_path: str = "./sessions"):
        self.session_id = session_id
        
        # Initialize all feature modules
        self.intent_analyzer = IntentAnalyzer()
        self.confidence_scorer = ConfidenceScorer()
        self.option_generator = OptionGenerator()
        self.blueprint_generator = BlueprintGenerator()
        self.step_executor = StepExecutor()
        self.dependency_checker = DependencyChecker()
        self.intervention_trigger = InterventionTrigger()
        self.replan_engine = ReplanEngine()
        self.state_persistence = StatePersistence(persistence_path)
        
        # State
        self.thinking_chain = ThinkingChain(session_id)
        self.execution_steps: List[ExecutionStep] = []
        self.completed_steps: List[ExecutionStep] = []
        self.failed_steps: List[ExecutionStep] = []
        
        # Current intent (reconstructed from thinking chain)
        self._current_intent: Optional[IntentAnalysis] = None
        
        # Callbacks for WebSocket layer
        self.callbacks: Dict[str, Callable] = {}
        
        # Register skill handlers (to be extended)
        self._register_default_skills()
    
    def _register_default_skills(self):
        """Register default skill handlers"""
        # Mock skills for testing - will be replaced with real skills
        from blueclaw.core import SkillHandler
        
        class MockSkill(SkillHandler):
            async def run(self, **kwargs) -> Any:
                class Result:
                    def __init__(self):
                        self.success = True
                        self.data = "Mock execution result"
                        self.metadata = {}
                return Result()
        
        self.step_executor.register_skill("mock", MockSkill())
    
    def set_callbacks(self, **callbacks):
        """Set callbacks for WebSocket notifications"""
        self.callbacks = callbacks
        self.step_executor.on_step_start = callbacks.get('on_step_started') or callbacks.get('on_step_start')
        self.step_executor.on_step_complete = callbacks.get('on_step_completed') or callbacks.get('on_step_complete')
        self.step_executor.on_step_failed = callbacks.get('on_step_failed') or callbacks.get('on_step_fail')
    
    # ========== Thinking Phase ==========
    
    async def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input (thinking phase entry)
        
        Flow:
        1. Intent analysis
        2. Confidence calculation
        3. Decision: direct execution / generate options
        """
        # Intent analysis
        intent = self.intent_analyzer.analyze(user_input)
        self._current_intent = intent
        
        # Create root node if not exists
        if not self.thinking_chain.root_node_id:
            self.thinking_chain.create_root_node(user_input, options=[])
        
        # Check if it's an option selection
        if intent.intent_type == IntentType.CLARIFICATION:
            return await self._handle_option_selection(user_input)
        
        # Calculate confidence
        confidence = self.confidence_scorer.score(intent, {
            "thinking_chain": self.thinking_chain
        })
        
        # High confidence: direct execution preview
        if confidence.can_auto_execute():
            steps = self.blueprint_generator.generate(
                self.thinking_chain, intent
            )
            self.execution_steps = steps
            return {
                "type": "execution_preview",
                "steps": self._steps_to_dict(steps),
                "confidence": confidence.value,
                "session_id": self.session_id
            }
        
        # Low confidence: generate clarification options
        options = self.option_generator.generate(
            intent,
            self.thinking_chain.current_node_id
        )
        
        node = self.thinking_chain.add_clarification_node(
            self.thinking_chain.current_node_id,
            question=self._generate_question(intent),
            options=options
        )
        
        return {
            "type": "thinking_node",
            "node_id": node.node_id,
            "question": node.question,
            "options": options,
            "session_id": self.session_id
        }
    
    async def _handle_option_selection(self, user_input: str) -> Dict[str, Any]:
        """Handle user selecting an option"""
        # Parse option from input (simplified)
        # In real implementation, would parse option_id from input
        return await self.process(user_input)
    
    async def select_option(self, node_id: str, option_id: str) -> Dict[str, Any]:
        """User selects an option"""
        self.thinking_chain.resolve_node(node_id, option_id)
        
        # Check if converged
        if self.thinking_chain.is_converged():
            # Generate execution blueprint
            intent = self._reconstruct_intent()
            steps = self.blueprint_generator.generate(
                self.thinking_chain, intent
            )
            self.execution_steps = steps
            return {
                "type": "blueprint_ready",
                "steps": self._steps_to_dict(steps),
                "session_id": self.session_id
            }
        
        # Continue thinking, generate next question
        return await self.process("")
    
    def _generate_question(self, intent: IntentAnalysis) -> str:
        """Generate clarification question based on intent"""
        if intent.task_type:
            return f"请提供更多关于{intent.task_type.value}任务的详细信息"
        return "请提供更多详细信息以便更好地帮助您"
    
    def _reconstruct_intent(self) -> IntentAnalysis:
        """Reconstruct intent from thinking chain"""
        # Simplified: use current intent or create from chain
        if self._current_intent:
            return self._current_intent
        return IntentAnalysis(
            intent_type=IntentType.TASK,
            raw_input="Reconstructed from chain"
        )
    
    def _steps_to_dict(self, steps: List[ExecutionStep]) -> List[Dict]:
        """Convert steps to dictionary for JSON serialization"""
        result = []
        for step in steps:
            result.append({
                "step_id": step.step_id,
                "name": step.name,
                "description": step.description,
                "status": step.status.value,
                "dependencies": step.dependencies,
                "tool": step.tool
            })
        return result
    
    # ========== Execution Phase ==========
    
    async def execute_blueprint(self, steps: List[ExecutionStep] = None) -> Dict[str, Any]:
        """Execute blueprint"""
        if steps:
            self.execution_steps = steps
        
        self._notify('on_execution_started', {
            "session_id": self.session_id,
            "total_steps": len(self.execution_steps)
        })
        
        while True:
            # Get executable steps
            executable = self.dependency_checker.get_executable_steps(
                self.execution_steps,
                self.completed_steps
            )
            
            if not executable:
                # No executable steps, check if all completed
                if all(s.status == StepStatus.COMPLETED for s in self.execution_steps):
                    self._notify('on_execution_completed', {
                        "session_id": self.session_id,
                        "completed_steps": len(self.completed_steps)
                    })
                    return {"status": "completed", "session_id": self.session_id}
                
                # Check for failed steps blocking execution
                failed_pending = [s for s in self.execution_steps 
                                 if s.status == StepStatus.FAILED and s not in self.failed_steps]
                if failed_pending:
                    self.failed_steps.extend(failed_pending)
                    return {"status": "waiting_intervention", "session_id": self.session_id}
                
                break  # Wait for dependencies
            
            # Execute steps (parallel support)
            tasks = []
            for step in executable[:3]:  # Max 3 parallel
                tasks.append(self._execute_step_with_handling(step))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Save state
            self._save_state()
        
        return {"status": "in_progress", "session_id": self.session_id}
    
    async def _execute_step_with_handling(self, step: ExecutionStep):
        """Execute a single step with error handling"""
        result = await self.step_executor.execute_step(step)
        
        if result.success:
            self.completed_steps.append(step)
        else:
            # Check if intervention needed
            if self.intervention_trigger.should_intervene(step):
                self._notify('on_intervention_needed', {
                    "session_id": self.session_id,
                    "step_id": step.step_id,
                    "error": str(result.data) if hasattr(result, 'data') else "Unknown error"
                })
            else:
                # Record retry
                self.intervention_trigger.record_retry(step.step_id)
    
    # ========== Intervention Phase ==========
    
    async def intervene(
        self,
        step_id: str,
        action_type: str,
        custom_input: str = None
    ) -> Dict[str, Any]:
        """
        Handle intervention
        
        Actions:
        - replan: Trigger replanning
        - skip: Skip current step
        - stop: Stop execution
        - retry: Retry execution
        """
        failed_step = self._get_step_by_id(step_id)
        
        if action_type == "replan":
            # REPLAN logic
            intervention_context = {
                "user_input": custom_input,
                "failed_step": failed_step,
                "completed_steps": self.completed_steps
            }
            
            # Keep completed, replan remaining
            kept_steps, new_steps = self.replan_engine.replan(
                self.execution_steps,
                failed_step,
                intervention_context
            )
            
            # Update step list
            self.execution_steps = kept_steps + new_steps
            
            self._notify('on_blueprint_replaned', {
                "session_id": self.session_id,
                "kept_count": len(kept_steps),
                "new_count": len(new_steps)
            })
            
            return {
                "type": "blueprint_replaned",
                "kept_steps": self._steps_to_dict(kept_steps),
                "new_steps": self._steps_to_dict(new_steps),
                "session_id": self.session_id
            }
        
        elif action_type == "skip":
            # Skip current step
            failed_step.status = StepStatus.SKIPPED
            self.completed_steps.append(failed_step)
            
            self._notify('on_step_skipped', {
                "session_id": self.session_id,
                "step_id": step_id
            })
            
            # Continue execution
            return await self.execute_blueprint()
        
        elif action_type == "stop":
            # Stop execution
            self._notify('on_execution_stopped', {
                "session_id": self.session_id,
                "completed_steps": len(self.completed_steps)
            })
            return {"status": "stopped", "session_id": self.session_id}
        
        elif action_type == "retry":
            # Retry
            failed_step.status = StepStatus.PENDING
            return await self.execute_blueprint()
        
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def get_intervention_actions(self, step_id: str) -> List[Dict[str, str]]:
        """Get available intervention actions for a failed step"""
        step = self._get_step_by_id(step_id)
        return self.intervention_trigger.get_intervention_actions(step)
    
    # ========== Utility Methods ==========
    
    def _save_state(self):
        """Save session state"""
        self.state_persistence.save_session(
            self.session_id,
            self.thinking_chain,
            self.execution_steps
        )
    
    def load_session(self, session_id: str) -> bool:
        """Load session state"""
        data = self.state_persistence.load_session(session_id)
        if data:
            # Restore state (simplified)
            self.session_id = session_id
            return True
        return False
    
    def _get_step_by_id(self, step_id: str) -> ExecutionStep:
        """Get step by ID"""
        for step in self.execution_steps:
            if step.step_id == step_id:
                return step
        raise ValueError(f"Step not found: {step_id}")
    
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
    
    # ========== Status Queries ==========
    
    def get_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        return {
            "session_id": self.session_id,
            "thinking_phase": self.thinking_chain.is_converged(),
            "total_steps": len(self.execution_steps),
            "completed_steps": len(self.completed_steps),
            "failed_steps": len(self.failed_steps),
            "progress": len(self.completed_steps) / len(self.execution_steps) * 100 
                       if self.execution_steps else 0
        }
    
    def get_thinking_chain(self) -> Dict[str, Any]:
        """Get thinking chain data"""
        return {
            "session_id": self.session_id,
            "root_node_id": self.thinking_chain.root_node_id,
            "current_node_id": self.thinking_chain.current_node_id,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "content": n.content,
                    "status": n.status.value if hasattr(n.status, 'value') else n.status,
                    "node_type": n.node_type
                }
                for n in self.thinking_chain.nodes.values()
            ]
        }
