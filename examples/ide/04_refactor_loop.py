#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 04: Refactor Loop

Demonstrates a refactoring task using the modification loop:
1. Provide a function with duplicated logic
2. Mock code model generates an extraction refactor
3. Sandbox validates syntax

Run: python examples/ide/04_refactor_loop.py
"""
import asyncio
import os
import tempfile

from blueclaw.adapter.ide.loop import ModificationLoop, LoopConfig
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator

CODE = """def process_orders(orders):
    results = []
    for o in orders:
        # duplicated validation
        if not o.get('id'):
            raise ValueError('missing id')
        if not o.get('amount'):
            raise ValueError('missing amount')
        results.append(o)
    return results

def process_refunds(refunds):
    results = []
    for r in refunds:
        if not r.get('id'):
            raise ValueError('missing id')
        if not r.get('amount'):
            raise ValueError('missing amount')
        results.append(r)
    return results
"""


async def main():
    tmpdir = tempfile.mkdtemp()

    with open(os.path.join(tmpdir, "orders.py"), "w", encoding="utf-8") as f:
        f.write(CODE)

    loop = ModificationLoop(
        code_model=MockCodeModelClient(),
        sandbox=SandboxValidator(project_path=tmpdir),
        config=LoopConfig(max_iterations=2, enable_auto_apply=False),
    )

    print("[RUN] Starting refactor loop ...")
    result = await loop.run(
        task_description="Extract the duplicated validation into a helper function _validate_item",
        file_context={"orders.py": CODE},
    )

    print(f"[RESULT] Success: {result.success}")
    print(f"[RESULT] Iterations: {result.iterations}")
    for line in result.debug_log[-10:]:
        print(f"  {line}")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 04 complete.")


if __name__ == "__main__":
    asyncio.run(main())
