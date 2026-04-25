#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Skills Tests"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import asyncio
from blueclaw.skills import AISummarizeSkill, AITranslateSkill


class TestAISkills:
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
        print("AI Skills Tests")
        print("="*60)
        
        await self.test_summarize()
        await self.test_translate()
        
        print("\n" + "="*60)
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed ({self.passed/total*100:.1f}%)")
        print("="*60)
        return self.failed == 0
    
    async def test_summarize(self):
        print("\n[1] AISummarizeSkill")
        skill = AISummarizeSkill()
        
        # Test 1: Summarize text
        text = "This is a long text. It has multiple sentences. " * 10
        result = await skill.run(text=text, max_length=100)
        self.assert_true(result.success, "Summarize text")
        self.assert_true(len(result.output) <= 100, "Summary within limit")
        
        # Test 2: Empty text
        result = await skill.run(text="")
        self.assert_true(not result.success, "Empty text fails")
    
    async def test_translate(self):
        print("\n[2] AITranslateSkill")
        skill = AITranslateSkill()
        
        # Test 1: Translate
        result = await skill.run(text="Hello", target_language="zh")
        self.assert_true(result.success, "Translate")
        self.assert_true(result.output is not None, "Has output")
        
        # Test 2: Detect language
        result = await skill.run(text="你好", target_language="en", 
                                  source_language="auto")
        self.assert_true(result.metadata.get("source_language") == "zh", "Auto detect")


async def main():
    test = TestAISkills()
    success = await test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
