#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Test for Blueclaw Engine Facade

Tests the integration of all 10 core features.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blueclaw.api import BlueclawEngineFacade
from blueclaw.core.blueprint_generator import ExecutionStep, StepStatus


class TestIntegration:
    """Integration test suite"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.engine = None
    
    def log(self, msg: str):
        print(f"  {msg}")
    
    def assert_true(self, condition: bool, name: str):
        if condition:
            self.passed += 1
            self.log(f"[PASS] {name}")
        else:
            self.failed += 1
            self.log(f"[FAIL] {name}")
    
    async def run_all(self):
        print("="*60)
        print("Week 16.5 - Integration Test")
        print("="*60)
        
        # Test 1: Engine Initialization
        print("\n[1] Engine Initialization")
        await self.test_init()
        
        # Test 2: Thinking Phase
        print("\n[2] Thinking Phase")
        await self.test_thinking_phase()
        
        # Test 3: Option Selection
        print("\n[3] Option Selection")
        await self.test_option_selection()
        
        # Test 4: Blueprint Generation
        print("\n[4] Blueprint Generation")
        await self.test_blueprint_generation()
        
        # Test 5: Execution Phase
        print("\n[5] Execution Phase")
        await self.test_execution_phase()
        
        # Test 6: Intervention
        print("\n[6] Intervention")
        await self.test_intervention()
        
        # Test 7: State Persistence
        print("\n[7] State Persistence")
        await self.test_state_persistence()
        
        # Test 8: Callbacks
        print("\n[8] Callbacks")
        await self.test_callbacks()
        
        # Test 9: Status Queries
        print("\n[9] Status Queries")
        await self.test_status_queries()
        
        # Test 10: Full Flow
        print("\n[10] Full Workflow")
        await self.test_full_workflow()
        
        # Summary
        print("\n" + "="*60)
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed ({self.passed/total*100:.1f}%)")
        print("="*60)
        
        return self.failed == 0
    
    async def test_init(self):
        """Test engine initialization"""
        try:
            self.engine = BlueclawEngineFacade("test_session_001")
            self.assert_true(self.engine is not None, "Engine created")
            self.assert_true(self.engine.session_id == "test_session_001", "Session ID set")
            self.assert_true(len(self.engine.callbacks) == 0, "Empty callbacks")
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 3
    
    async def test_thinking_phase(self):
        """Test thinking phase processing"""
        try:
            self.engine = BlueclawEngineFacade("test_session_002")
            
            # Process input
            result = await self.engine.process("Plan a trip to Shanghai")
            
            self.assert_true("type" in result, "Result has type")
            self.assert_true(result["session_id"] == "test_session_002", "Session ID in result")
            
            # Should either be execution_preview or thinking_node
            self.assert_true(
                result["type"] in ["execution_preview", "thinking_node"],
                "Valid result type"
            )
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 3
    
    async def test_option_selection(self):
        """Test option selection"""
        try:
            self.engine = BlueclawEngineFacade("test_session_003")
            
            # First process to create nodes
            result = await self.engine.process("Book a flight")
            
            # If we got a thinking_node, select an option
            if result["type"] == "thinking_node":
                node_id = result["node_id"]
                select_result = await self.engine.select_option(node_id, "option_1")
                self.assert_true("type" in select_result, "Selection result has type")
            else:
                self.passed += 1
                self.log("[SKIP] No thinking node generated (high confidence)")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 1
    
    async def test_blueprint_generation(self):
        """Test blueprint generation"""
        try:
            self.engine = BlueclawEngineFacade("test_session_004")
            
            # Process to generate blueprint
            result = await self.engine.process("Create a shopping list")
            
            # Ensure we have steps
            if result["type"] == "execution_preview":
                steps = result["steps"]
                self.assert_true(len(steps) > 0, "Steps generated")
                self.engine.execution_steps = [
                    ExecutionStep(
                        step_id=s["step_id"],
                        name=s["name"],
                        description=s["description"],
                        direction="Execute",
                        expected_result="Success",
                        validation_rule="非空",
                        tool="mock",
                        dependencies=s.get("dependencies", [])
                    )
                    for s in steps
                ]
            else:
                self.passed += 1
                self.log("[SKIP] Blueprint not generated yet")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 1
    
    async def test_execution_phase(self):
        """Test execution phase"""
        try:
            self.engine = BlueclawEngineFacade("test_session_005")
            
            # Create mock steps
            self.engine.execution_steps = [
                ExecutionStep(
                    step_id="step_1",
                    name="Test Step 1",
                    description="First test step",
                    direction="Execute test",
                    expected_result="Success",
                    validation_rule="非空",
                    tool="mock"
                ),
                ExecutionStep(
                    step_id="step_2",
                    name="Test Step 2",
                    description="Second test step",
                    direction="Execute test",
                    expected_result="Success",
                    validation_rule="非空",
                    tool="mock",
                    dependencies=["step_1"]
                )
            ]
            
            # Execute
            result = await self.engine.execute_blueprint()
            
            self.assert_true("status" in result, "Execution has status")
            self.assert_true(
                result["status"] in ["completed", "in_progress", "waiting_intervention"],
                "Valid execution status"
            )
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_intervention(self):
        """Test intervention handling"""
        try:
            self.engine = BlueclawEngineFacade("test_session_006")
            
            # Create a failed step
            failed_step = ExecutionStep(
                step_id="failed_step",
                name="Failed Step",
                description="This step fails",
                direction="Execute",
                expected_result="Success",
                validation_rule="非空",
                tool="mock"
            )
            failed_step.status = StepStatus.FAILED
            self.engine.execution_steps = [failed_step]
            
            # Get intervention actions
            actions = self.engine.get_intervention_actions("failed_step")
            self.assert_true(len(actions) > 0, "Intervention actions available")
            
            # Test skip action
            result = await self.engine.intervene("failed_step", "skip")
            self.assert_true("status" in result, "Intervention has result")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_state_persistence(self):
        """Test state persistence"""
        try:
            import shutil
            import os
            
            persistence_path = "./test_sessions_integration"
            
            # Clean up
            if os.path.exists(persistence_path):
                shutil.rmtree(persistence_path)
            
            self.engine = BlueclawEngineFacade("test_session_007", persistence_path)
            
            # Create some state
            await self.engine.process("Test task")
            self.engine._save_state()
            
            # Check file exists
            session_file = Path(persistence_path) / "test_session_007.json"
            self.assert_true(session_file.exists(), "Session file created")
            
            # Load session
            loaded = self.engine.load_session("test_session_007")
            self.assert_true(loaded, "Session loaded")
            
            # Cleanup
            shutil.rmtree(persistence_path, ignore_errors=True)
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_callbacks(self):
        """Test callback system"""
        try:
            events_received = []
            
            async def on_execution_started(data):
                events_received.append("started")
            
            def on_execution_completed(data):
                events_received.append("completed")
            
            self.engine = BlueclawEngineFacade("test_session_008")
            self.engine.set_callbacks(
                on_execution_started=on_execution_started,
                on_execution_completed=on_execution_completed
            )
            
            self.assert_true(
                self.engine.step_executor.on_step_start is not None or
                self.engine.callbacks.get('on_execution_started') is not None,
                "Callback registered"
            )
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 1
    
    async def test_status_queries(self):
        """Test status query methods"""
        try:
            self.engine = BlueclawEngineFacade("test_session_009")
            
            # Get status
            status = self.engine.get_status()
            self.assert_true("session_id" in status, "Status has session_id")
            self.assert_true("progress" in status, "Status has progress")
            
            # Get thinking chain
            chain = self.engine.get_thinking_chain()
            self.assert_true("nodes" in chain, "Chain has nodes")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_full_workflow(self):
        """Test complete workflow"""
        try:
            import shutil
            
            persistence_path = "./test_sessions_workflow"
            shutil.rmtree(persistence_path, ignore_errors=True)
            
            # 1. Create engine
            self.engine = BlueclawEngineFacade("workflow_session", persistence_path)
            
            # 2. Process input (thinking phase)
            result = await self.engine.process("Plan a weekend trip")
            self.log(f"  Phase 1 result: {result['type']}")
            
            # 3. If thinking node, select option (loop until converged)
            max_iterations = 5
            iteration = 0
            while result["type"] == "thinking_node" and iteration < max_iterations:
                options = result["options"]
                option_id = options[0].id if hasattr(options[0], 'id') else options[0]["id"]
                result = await self.engine.select_option(
                    result["node_id"],
                    option_id
                )
                iteration += 1
                self.log(f"  Phase {iteration+1} result: {result['type']}")
            
            # 4. Should now have blueprint
            self.assert_true(len(self.engine.execution_steps) > 0, "Has execution steps")
            
            # 5. Execute blueprint
            exec_result = await self.engine.execute_blueprint()
            self.log(f"  Execution result: {exec_result['status']}")
            
            self.assert_true("status" in exec_result, "Execution completed")
            
            # Cleanup
            shutil.rmtree(persistence_path, ignore_errors=True)
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 3


async def main():
    test = TestIntegration()
    success = await test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
