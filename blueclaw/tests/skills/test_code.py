#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code Skills Tests"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import asyncio
from blueclaw.skills import CodeAnalyzeSkill, CodeExecuteSkill


class TestCodeSkills:
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def assert_true(self, condition, name):
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {name}")
    
    async def run_all(self):
        print("="*60)
        print("Code Skills Tests")
        print("="*60)
        
        await self.test_analyze()
        await self.test_execute()
        
        print("\n" + "="*60)
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed ({self.passed/total*100:.1f}%)")
        print("="*60)
        return self.failed == 0
    
    async def test_analyze(self):
        print("\n[1] CodeAnalyzeSkill")
        skill = CodeAnalyzeSkill()
        
        # Test 1: Analyze Python code
        code = """
def hello():
    pass

class MyClass:
    def method(self):
        return 42
"""
        result = await skill.run(code=code, language="python")
        self.assert_true(result.success, "Analyze Python code")
        metrics = result.output.get("metrics", {})
        self.assert_true(metrics.get("functions", 0) >= 1, "Function count")
        self.assert_true(metrics.get("classes", 0) >= 1, "Class count")
        
        # Test 2: Analyze with syntax error
        code = "def broken("
        result = await skill.run(code=code, language="python")
        self.assert_true(result.success, "Handles syntax error gracefully")
    
    async def test_execute(self):
        print("\n[2] CodeExecuteSkill")
        skill = CodeExecuteSkill()
        
        # Test 1: Simple calculation
        result = await skill.run(code="result = 2 + 2 * 10")
        self.assert_true(result.success, "Execute simple code")
        
        # Test 2: List comprehension
        result = await skill.run(code="[x**2 for x in range(5)]")
        self.assert_true(result.success, "Execute list comprehension")
        
        # Test 3: Blocked dangerous code
        result = await skill.run(code="import os")
        self.assert_true(not result.success, "Blocks import")


async def main():
    test = TestCodeSkills()
    success = await test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
