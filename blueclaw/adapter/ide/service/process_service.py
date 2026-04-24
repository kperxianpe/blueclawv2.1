# -*- coding: utf-8 -*-
"""
Process Service - 子进程执行管理

- 运行代码文件
- 实时输出推送（SSE / WebSocket）
- 进程终止
"""
import asyncio
import os
import sys
import time
import uuid
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field

from blueclaw.adapter.ide.models import RunRequest, RunResult, RunOutputChunk


@dataclass
class _ProcessRecord:
    run_id: str
    proc: asyncio.subprocess.Process
    start_time: float
    status: str = "running"
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    callbacks: list = field(default_factory=list)


class ProcessService:
    """进程执行服务"""

    def __init__(self):
        self._runs: Dict[str, _ProcessRecord] = {}

    def _infer_command(self, req: RunRequest, workspace_path: str) -> str:
        """自动推断执行命令"""
        if req.command:
            return req.command
        if req.path:
            ext = os.path.splitext(req.path)[1].lower()
            abs_path = os.path.join(req.cwd or workspace_path, req.path)
            if ext == ".py":
                return f"{sys.executable} \"{abs_path}\""
            elif ext in (".js", ".mjs"):
                return f"node \"{abs_path}\""
            elif ext == ".sh":
                return f"bash \"{abs_path}\""
            elif ext == ".html":
                return f"echo 'Open in browser: {abs_path}'"
        return "echo 'No command specified'"

    async def start(self, req: RunRequest, workspace_path: str, output_callback: Optional[Callable] = None) -> RunResult:
        """启动进程"""
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        command = self._infer_command(req, workspace_path)
        cwd = req.cwd or workspace_path

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                env={**os.environ, **req.env},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            return RunResult(run_id=run_id, command=command, status="failed", stderr=str(e))

        record = _ProcessRecord(run_id=run_id, proc=proc, start_time=time.time())
        if output_callback:
            record.callbacks.append(output_callback)
        self._runs[run_id] = record

        # Start background readers
        asyncio.create_task(self._read_stdout(record))
        asyncio.create_task(self._read_stderr(record))
        asyncio.create_task(self._wait_exit(record))

        return RunResult(run_id=run_id, command=command, status="running")

    async def _read_stdout(self, record: _ProcessRecord):
        if record.proc.stdout:
            while True:
                try:
                    line = await record.proc.stdout.read(1024)
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    record.stdout += text
                    await self._notify(record, RunOutputChunk(run_id=record.run_id, type="stdout", data=text))
                except Exception:
                    break

    async def _read_stderr(self, record: _ProcessRecord):
        if record.proc.stderr:
            while True:
                try:
                    line = await record.proc.stderr.read(1024)
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    record.stderr += text
                    await self._notify(record, RunOutputChunk(run_id=record.run_id, type="stderr", data=text))
                except Exception:
                    break

    async def _wait_exit(self, record: _ProcessRecord):
        try:
            exit_code = await record.proc.wait()
            record.exit_code = exit_code
            record.status = "completed" if exit_code == 0 else "failed"
            duration = (time.time() - record.start_time) * 1000
            await self._notify(record, RunOutputChunk(
                run_id=record.run_id, type="exit", data="", exit_code=exit_code,
            ))
        except Exception as e:
            record.status = "failed"
            record.stderr += str(e)

    async def _notify(self, record: _ProcessRecord, chunk: RunOutputChunk):
        for cb in record.callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(chunk)
                else:
                    cb(chunk)
            except Exception:
                pass

    def get_result(self, run_id: str) -> Optional[RunResult]:
        record = self._runs.get(run_id)
        if not record:
            return None
        return RunResult(
            run_id=record.run_id,
            command=record.proc._transport.get_extra_info("subprocess_command") if hasattr(record.proc, "_transport") else "",
            status=record.status,
            exit_code=record.exit_code,
            stdout=record.stdout,
            stderr=record.stderr,
            duration_ms=(time.time() - record.start_time) * 1000,
        )

    async def kill(self, run_id: str) -> bool:
        record = self._runs.get(run_id)
        if not record or record.status != "running":
            return False
        try:
            record.proc.kill()
            record.status = "killed"
            return True
        except Exception:
            return False
