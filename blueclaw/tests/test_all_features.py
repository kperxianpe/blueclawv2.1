#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test all 10 core features"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def run_tests():
    print("="*60)
    print("Week 16 - Testing 10 Core Features")
    print("="*60)
    
    total_pass = 0
    total_fail = 0
    
    # Test 1: Intent Analyzer
    print("\n[1] Intent Analyzer...")
    try:
        from blueclaw.core.intent_analyzer import IntentAnalyzer, IntentType
        analyzer = IntentAnalyzer()
        result = analyzer.analyze("Plan a trip to Shanghai")
        assert result.intent_type == IntentType.TASK
        assert result.task_type.value == "travel_planning"
        print("    [PASS] Intent detection")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 2: Confidence Scorer
    print("\n[2] Confidence Scorer...")
    try:
        from blueclaw.core.confidence_scorer import ConfidenceScorer
        from blueclaw.core.intent_analyzer import IntentAnalysis, IntentType
        scorer = ConfidenceScorer()
        intent = IntentAnalysis(intent_type=IntentType.TASK, raw_input="Plan a trip")
        score = scorer.score(intent)
        assert 0 <= score.value <= 1
        print(f"    [PASS] Score: {score.value:.2f}")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 3: Option Generator
    print("\n[3] Option Generator...")
    try:
        from blueclaw.core.option_generator import OptionGenerator
        from blueclaw.core.intent_analyzer import IntentAnalysis, IntentType, TaskType
        generator = OptionGenerator()
        intent = IntentAnalysis(intent_type=IntentType.TASK, task_type=TaskType.TRAVEL_PLANNING)
        options = generator.generate(intent, "node_001")
        assert len(options) >= 2
        print(f"    [PASS] Generated {len(options)} options")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 4: Thinking Chain
    print("\n[4] Thinking Chain...")
    try:
        from blueclaw.core.thinking_chain import ThinkingChain
        chain = ThinkingChain("session_001")
        root = chain.create_root_node("Plan trip")
        node = chain.add_clarification_node(root.node_id, "Where to?", [{"id": "A", "label": "Shanghai"}])
        chain.resolve_node(node.node_id, "A")
        assert node.status.value == "resolved"
        print("    [PASS] Chain operations")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 5: Blueprint Generator
    print("\n[5] Blueprint Generator...")
    try:
        from blueclaw.core.blueprint_generator import BlueprintGenerator
        from blueclaw.core.thinking_chain import ThinkingChain
        from blueclaw.core.intent_analyzer import IntentAnalysis, IntentType, TaskType
        generator = BlueprintGenerator()
        chain = ThinkingChain("s1")
        chain.create_root_node("Plan")
        intent = IntentAnalysis(intent_type=IntentType.TASK, task_type=TaskType.TRAVEL_PLANNING)
        steps = generator.generate(chain, intent)
        assert len(steps) >= 2
        print(f"    [PASS] Generated {len(steps)} steps")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 6: Step Executor
    print("\n[6] Step Executor...")
    try:
        import asyncio
        from blueclaw.core.step_executor import StepExecutor
        from blueclaw.core.blueprint_generator import ExecutionStep, StepStatus
        
        class MockSkill:
            async def run(self, **kwargs):
                return type('Result', (), {'success': True, 'data': 'ok', 'metadata': {}})()
        
        executor = StepExecutor()
        executor.register_skill("mock", MockSkill())
        
        step = ExecutionStep(
            step_id="s1", name="Test", description="Test",
            direction="Test", expected_result="ok", 
            validation_rule="非空", tool="mock"
        )
        
        async def test():
            return await executor.execute_step(step)
        
        result = asyncio.run(test())
        assert result.success
        print("    [PASS] Step execution")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 7: Dependency Checker
    print("\n[7] Dependency Checker...")
    try:
        from blueclaw.core.dependency_checker import DependencyChecker
        from blueclaw.core.blueprint_generator import ExecutionStep, StepStatus
        
        checker = DependencyChecker()
        step = ExecutionStep(
            step_id="s1", name="Test", description="Test",
            direction="Test", expected_result="ok",
            validation_rule="非空", tool="mock", dependencies=[]
        )
        assert checker.check_dependencies(step, [])
        print("    [PASS] Dependency check")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 8: Intervention Trigger
    print("\n[8] Intervention Trigger...")
    try:
        from blueclaw.core.intervention_trigger import InterventionTrigger
        from blueclaw.core.blueprint_generator import ExecutionStep, StepStatus
        
        trigger = InterventionTrigger()
        step = ExecutionStep(
            step_id="s1", name="Test", description="Test",
            direction="Test", expected_result="ok",
            validation_rule="非空", tool="mock"
        )
        step.status = StepStatus.FAILED
        trigger.record_retry("s1")
        trigger.record_retry("s1")
        
        assert trigger.should_intervene(step)
        print("    [PASS] Intervention trigger")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 9: Replan Engine
    print("\n[9] Replan Engine...")
    try:
        from blueclaw.core.replan_engine import ReplanEngine
        from blueclaw.core.blueprint_generator import ExecutionStep, StepStatus
        
        engine = ReplanEngine()
        steps = [
            ExecutionStep("s1", "Step1", "Desc", "Dir", "Result", "非空", "mock"),
            ExecutionStep("s2", "Step2", "Desc", "Dir", "Result", "非空", "mock"),
        ]
        steps[0].status = StepStatus.COMPLETED
        
        result = engine._handle_skip(steps, steps[0])
        assert result.success
        print("    [PASS] Replan logic")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Test 10: State Persistence
    print("\n[10] State Persistence...")
    try:
        import shutil
        from blueclaw.core.state_persistence import StatePersistence
        from blueclaw.core.thinking_chain import ThinkingChain
        
        persistence = StatePersistence("./test_sessions")
        chain = ThinkingChain("test_session")
        chain.create_root_node("Test")
        
        file_path = persistence.save_session("test_session", chain, [])
        assert file_path.exists()
        
        data = persistence.load_session("test_session")
        assert data is not None
        
        persistence.delete_session("test_session")
        shutil.rmtree("./test_sessions", ignore_errors=True)
        
        print("    [PASS] State persistence")
        total_pass += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        total_fail += 1
    
    # Summary
    print("\n" + "="*60)
    print(f"Results: {total_pass} passed, {total_fail} failed")
    print(f"Success Rate: {total_pass/(total_pass+total_fail)*100:.1f}%")
    print("="*60)
    
    return total_fail == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
