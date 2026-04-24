# -*- coding: utf-8 -*-
"""
Runner API - 代码执行路由

POST /api/ide/run/execute
GET  /api/ide/run/output  (SSE)
POST /api/ide/run/kill
"""
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from blueclaw.adapter.ide.models import RunRequest, RunResult, RunOutputChunk
from blueclaw.adapter.ide.service.process_service import ProcessService
from blueclaw.adapter.ide.service.workspace import WorkspaceService


router = APIRouter(prefix="/run", tags=["IDE Runner"])

_workspace: WorkspaceService = WorkspaceService()
_process_service: ProcessService = ProcessService()


def set_workspace(ws: WorkspaceService):
    global _workspace
    _workspace = ws


@router.post("/execute", response_model=RunResult)
async def execute(req: RunRequest):
    """执行代码或命令"""
    result = await _process_service.start(req, _workspace.root_path, output_callback=None)
    return result


@router.get("/output")
async def stream_output(run_id: str):
    """SSE 流式获取执行输出"""
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        def on_output(chunk: RunOutputChunk):
            try:
                queue.put_nowait(chunk)
            except Exception:
                pass

        # Attach callback to existing run
        record = _process_service._runs.get(run_id)
        if record:
            record.callbacks.append(on_output)
            # Send existing buffered output first
            if record.stdout:
                yield f"data: {{\n\"type\": \"stdout\", \"data\": {repr(record.stdout)}\n}}\n\n"
            if record.stderr:
                yield f"data: {{\n\"type\": \"stderr\", \"data\": {repr(record.stderr)}\n}}\n\n"
            # Wait for new output or completion
            for _ in range(300):  # max ~30 seconds of polling
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
                    import json
                    yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                    if chunk.type == "exit":
                        break
                except asyncio.TimeoutError:
                    continue
        else:
            yield f"data: {{\n\"type\": \"error\", \"data\": \"Run not found: {run_id}\"\n}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/kill")
async def kill_run(run_id: str):
    """终止执行"""
    success = await _process_service.kill(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or not running")
    return {"success": True, "run_id": run_id}


@router.get("/result", response_model=RunResult)
async def get_result(run_id: str):
    """获取执行结果"""
    result = _process_service.get_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result
