#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filesystem Skills Tests
"""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import asyncio
from blueclaw.skills import FileReadSkill, FileWriteSkill, FileListSkill, FileSearchSkill


class TestFilesystemSkills:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_dir = None
    
    def assert_true(self, condition, name):
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {name}")
    
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        # Create test files
        (Path(self.test_dir) / "test.txt").write_text("Hello World\nLine 2\nLine 3", encoding='utf-8')
        (Path(self.test_dir) / "test.json").write_text('{"name": "test"}', encoding='utf-8')
        (Path(self.test_dir) / "sub").mkdir()
        (Path(self.test_dir) / "sub" / "nested.txt").write_text("Nested content", encoding='utf-8')
    
    def cleanup(self):
        import shutil
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    async def run_all(self):
        print("="*60)
        print("Filesystem Skills Tests")
        print("="*60)
        
        self.setup()
        
        try:
            await self.test_file_read()
            await self.test_file_write()
            await self.test_file_list()
            await self.test_file_search()
        finally:
            self.cleanup()
        
        # Summary
        print("\n" + "="*60)
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed ({self.passed/total*100:.1f}%)")
        print("="*60)
        
        return self.failed == 0
    
    async def test_file_read(self):
        print("\n[1] FileReadSkill")
        skill = FileReadSkill()
        
        # Test 1: Read existing file
        result = await skill.run(path=str(Path(self.test_dir) / "test.txt"))
        self.assert_true(result.success, "Read existing file")
        self.assert_true("Hello World" in str(result.output), "Content correct")
        
        # Test 2: Read with limit
        result = await skill.run(path=str(Path(self.test_dir) / "test.txt"), limit_lines=1)
        self.assert_true(result.success, "Read with limit")
        self.assert_true(result.metadata.get("truncated") == True, "Truncated flag set")
        
        # Test 3: Read non-existent
        result = await skill.run(path=str(Path(self.test_dir) / "nonexistent.txt"))
        self.assert_true(not result.success, "Non-existent file fails")
    
    async def test_file_write(self):
        print("\n[2] FileWriteSkill")
        skill = FileWriteSkill()
        
        # Test 1: Write new file
        test_file = Path(self.test_dir) / "write_test.txt"
        result = await skill.run(path=str(test_file), content="Test content")
        self.assert_true(result.success, "Write new file")
        self.assert_true(test_file.exists(), "File created")
        
        # Test 2: Append mode
        result = await skill.run(path=str(test_file), content="\nAppended", append=True)
        self.assert_true(result.success, "Append to file")
        content = test_file.read_text()
        self.assert_true("Appended" in content, "Content appended")
    
    async def test_file_list(self):
        print("\n[3] FileListSkill")
        skill = FileListSkill()
        
        # Test 1: List directory
        result = await skill.run(path=self.test_dir)
        self.assert_true(result.success, "List directory")
        items = result.output.get("items", [])
        self.assert_true(len(items) >= 3, f"Has items (found {len(items)})")
        
        # Test 2: Recursive list
        result = await skill.run(path=self.test_dir, recursive=True)
        self.assert_true(result.success, "Recursive list")
        nested_found = any("nested.txt" in i.get("name", "") for i in result.output.get("items", []))
        self.assert_true(nested_found, "Nested file found")
    
    async def test_file_search(self):
        print("\n[4] FileSearchSkill")
        skill = FileSearchSkill()
        
        # Test 1: Search content
        result = await skill.run(pattern="Hello", path=self.test_dir)
        self.assert_true(result.success, "Search content")
        matches = result.output.get("matches", [])
        self.assert_true(len(matches) > 0, f"Found matches ({len(matches)})")
        
        # Test 2: Search with file pattern
        result = await skill.run(pattern="test", path=self.test_dir, file_pattern="*.txt")
        self.assert_true(result.success, "Search with pattern")


async def main():
    test = TestFilesystemSkills()
    success = await test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
