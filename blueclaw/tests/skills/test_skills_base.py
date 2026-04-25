#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills Base Tests

Tests for Skill base class, Registry, and ToolSelector.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import asyncio
from blueclaw.skills import Skill, SkillResult, SkillRegistry, ToolSelector


class TestSkillBase:
    """Test Skill base functionality"""
    
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
        print("Skills Base Tests")
        print("="*60)
        
        # Test 1: SkillResult creation
        print("\n[1] SkillResult")
        result = SkillResult(success=True, output="test")
        self.assert_true(result.success, "Result created")
        self.assert_true(result.output == "test", "Output set")
        
        # Test 2: SkillRegistry
        print("\n[2] SkillRegistry")
        skills = SkillRegistry.list_all()
        self.assert_true(len(skills) >= 15, f"Has 15+ skills (found {len(skills)})")
        
        # Test 3: Get skill
        print("\n[3] Get Skill")
        skill = SkillRegistry.get("file_read")
        self.assert_true(skill is not None, "file_read exists")
        self.assert_true(skill.category == "filesystem", "Category correct")
        
        # Test 4: Categories
        print("\n[4] Categories")
        cats = SkillRegistry.get_categories()
        self.assert_true("filesystem" in cats, "filesystem category")
        self.assert_true("code" in cats, "code category")
        
        # Test 5: List by category
        print("\n[5] List by category")
        fs_skills = SkillRegistry.list_by_category("filesystem")
        self.assert_true(len(fs_skills) == 4, f"4 filesystem skills (found {len(fs_skills)})")
        
        # Test 6: ToolSelector
        print("\n[6] ToolSelector")
        selector = ToolSelector()
        tools = selector.get_tools_for_task("读取文件内容")
        self.assert_true("file_read" in tools, "file_read suggested for reading")
        
        # Test 7: Dangerous check
        print("\n[7] Dangerous check")
        dangerous = selector.check_dangerous_operations(["file_write", "shell_execute"])
        self.assert_true(len(dangerous) == 2, "2 dangerous operations found")
        
        # Test 8: Prompt generation
        print("\n[8] Prompt generation")
        prompt = selector.generate_tools_prompt(["file_read", "code_analyze"])
        self.assert_true("file_read" in prompt, "file_read in prompt")
        self.assert_true("code_analyze" in prompt, "code_analyze in prompt")
        
        # Summary
        print("\n" + "="*60)
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed ({self.passed/total*100:.1f}%)")
        print("="*60)
        
        return self.failed == 0


async def main():
    test = TestSkillBase()
    success = await test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
