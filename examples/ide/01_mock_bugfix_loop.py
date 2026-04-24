#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 01: Mock Bug Fix Loop

Demonstrates the full IDE modification pipeline using mock code model:
1. Provide a buggy Python file
2. MockCodeModelClient generates a fix diff
3. SandboxValidator checks syntax and tests
4. Loop completes successfully

Run: python examples/ide/01_mock_bugfix_loop.py
"""
import asyncio
import os
import tempfile

from blueclaw.adapter.ide.loop import ModificationLoop, LoopConfig
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier

BUGGY_CODE = """def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)  # Bug: divide by zero if empty

# Test
assert calculate_average([1, 2, 3]) == 2.0
"""


async def main():
    tmpdir = tempfile.mkdtemp()
    print(f"[INFO] Working in: {tmpdir}")

    # Write buggy file
    math_path = os.path.join(tmpdir, "math.py")
    with open(math_path, "w", encoding="utf-8") as f:
        f.write(BUGGY_CODE)

    loop = ModificationLoop(
        code_model=MockCodeModelClient(),
        sandbox=SandboxValidator(project_path=tmpdir),
        applier=IncrementApplier(project_path=tmpdir),
        config=LoopConfig(max_iterations=2, enable_auto_apply=False),
    )

    print("[RUN] Starting bug fix loop ...")
    result = await loop.run(
        task_description="Fix divide by zero when numbers list is empty",
        file_context={"math.py": BUGGY_CODE},
    )

    print(f"[RESULT] Success: {result.success}")
    print(f"[RESULT] Iterations: {result.iterations}")
    if result.final_validation:
        print(f"[RESULT] Validation checks: {len(result.final_validation.checks)}")
        for c in result.final_validation.checks:
            marker = "PASS" if c.passed else "FAIL"
            print(f"  [{marker}] {c.check_type}: {c.details}")
    if result.error:
        print(f"[RESULT] Error: {result.error}")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 01 complete.")


if __name__ == "__main__":
    asyncio.run(main())
