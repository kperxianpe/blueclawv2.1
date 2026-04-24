# -*- coding: utf-8 -*-
"""
Test Runner API - 测试执行路由

POST /api/ide/test/run
GET  /api/ide/test/result
"""
import asyncio
import os
import subprocess
import tempfile
from fastapi import APIRouter, HTTPException

from blueclaw.adapter.ide.models import TestRunRequest, TestRunResult, TestCaseResult
from blueclaw.adapter.ide.service.workspace import WorkspaceService


router = APIRouter(prefix="/test", tags=["IDE Test Runner"])

_workspace: WorkspaceService = WorkspaceService()
_test_results: dict = {}


def set_workspace(ws: WorkspaceService):
    global _workspace
    _workspace = ws


@router.post("/run", response_model=TestRunResult)
async def run_tests(req: TestRunRequest):
    """运行测试"""
    import uuid
    test_run_id = f"tr-{uuid.uuid4().hex[:8]}"
    cwd = req.cwd or _workspace.root_path
    abs_path = os.path.join(cwd, req.path) if req.path else cwd

    if req.runner == "pytest":
        cmd = ["python", "-m", "pytest", abs_path, "-v", "--tb=short", "--json-report"]
    else:
        cmd = ["python", "-m", "unittest", "discover", "-s", abs_path, "-p", req.pattern]

    # Run in background
    async def _run():
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")

        # Parse simple result from stdout
        total = passed = failed = skipped = 0
        cases = []
        for line in stdout_str.splitlines():
            if " passed" in line and " failed" in line:
                parts = line.replace(",", "").split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i-1])
                    elif p == "failed":
                        failed = int(parts[i-1])
                    elif p == "skipped":
                        skipped = int(parts[i-1])
                total = passed + failed + skipped

        _test_results[test_run_id] = TestRunResult(
            test_run_id=test_run_id,
            status="completed",
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            cases=cases,
            stdout=stdout_str,
            stderr=stderr_str,
        )

    asyncio.create_task(_run())
    return TestRunResult(test_run_id=test_run_id, status="running")


@router.get("/result", response_model=TestRunResult)
async def get_test_result(test_run_id: str):
    """获取测试结果"""
    result = _test_results.get(test_run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test run not found")
    return result
