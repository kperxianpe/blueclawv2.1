#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data Skills Tests"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import asyncio
from blueclaw.skills import DataParseSkill, DataTransformSkill


class TestDataSkills:
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
        print("Data Skills Tests")
        print("="*60)
        
        await self.test_parse()
        await self.test_transform()
        
        print("\n" + "="*60)
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed ({self.passed/total*100:.1f}%)")
        print("="*60)
        return self.failed == 0
    
    async def test_parse(self):
        print("\n[1] DataParseSkill")
        skill = DataParseSkill()
        
        # Test 1: Parse JSON
        result = await skill.run(source='{"name": "test", "value": 123}', 
                                  format="json", is_path=False)
        self.assert_true(result.success, "Parse JSON")
        self.assert_true(result.output.get("name") == "test", "JSON data correct")
        
        # Test 2: Parse CSV
        csv = "a,b,c\n1,2,3\n4,5,6"
        result = await skill.run(source=csv, format="csv", is_path=False)
        self.assert_true(result.success, "Parse CSV")
        self.assert_true(len(result.output) == 2, "CSV rows")
    
    async def test_transform(self):
        print("\n[2] DataTransformSkill")
        skill = DataTransformSkill()
        
        # Test 1: Filter
        data = {"items": [{"age": 20}, {"age": 30}, {"age": 25}]}
        result = await skill.run(data=data, operation="filter", 
                                  config={"field": "age", "min": 25})
        self.assert_true(result.success, "Filter data")
        self.assert_true(len(result.output) == 2, "Filtered count")
        
        # Test 2: Sort
        data = {"items": [{"name": "C"}, {"name": "A"}, {"name": "B"}]}
        result = await skill.run(data=data, operation="sort",
                                  config={"field": "name"})
        self.assert_true(result.success, "Sort data")
        self.assert_true(result.output[0]["name"] == "A", "Sorted order")


async def main():
    test = TestDataSkills()
    success = await test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
