#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方向 A：前端 <-> 后端 E2E 干预链路验证（V3 简化版）

核心策略：不依赖完整任务流程，直接测试干预消息路由。
步骤：
1. 连接 WS
2. 发送 task.start 启动真实任务
3. 走完 thinking -> selection（自动选A）
4. 等待 execution.step_started（提取 step_id）
5. 发送 freeze_request
6. 验证后端返回（freeze.confirmed 或错误消息）
7. 发送 submit_annotation
8. 验证后端返回

用法：确保后端已启动后运行：
    cd blueclawv2
    python tests/e2e_intervention_verify_v3.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import websockets

WS_URL = "ws://127.0.0.1:8006/ws"


def log(tag, msg):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] [{tag}] {msg}")


class Verifier:
    def __init__(self):
        self.ws = None
        self.step_id = None
        self.task_id = None
        self.passed = 0
        self.failed = 0
        self.closed = False

    def ok(self, step, msg):
        self.passed += 1
        log("OK", f"{step}: {msg}")

    def fail(self, step, msg):
        self.failed += 1
        log("FAIL", f"{step}: {msg}")

    async def connect(self):
        try:
            self.ws = await websockets.connect(WS_URL, ping_interval=20, ping_timeout=10)
            self.closed = False
            self.ok("CONNECT", f"WebSocket connected {WS_URL}")
            return True
        except Exception as e:
            self.fail("CONNECT", f"Cannot connect: {e}")
            return False

    async def send(self, msg_type, payload):
        if self.closed:
            log("WARN", "Connection closed, skipping send")
            return
        msg = {
            "type": msg_type,
            "payload": payload,
            "message_id": f"test_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
        }
        await self.ws.send(json.dumps(msg))
        log("SEND", msg_type)

    async def recv_one(self, timeout=30):
        if self.closed:
            return None
        try:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(raw)
            t = data.get("type", "unknown")
            log("RECV", t)
            if t == "error":
                log("INFO", f"Error payload: {data.get('payload', {})}")
            return data
        except asyncio.TimeoutError:
            return None
        except websockets.exceptions.ConnectionClosed as e:
            log("CLOSED", f"Connection closed: {e}")
            self.closed = True
            return {"_closed": True}
        except Exception as e:
            log("ERROR", f"Recv error: {e}")
            return None

    async def run(self):
        log("START", "=" * 60)
        log("START", "Blueclaw E2E Intervention Verification V3")
        log("START", f"WS: {WS_URL}")
        log("START", "This test sends real LLM requests, may take 60-120s")
        log("START", "=" * 60)

        # Phase 1: Connect
        if not await self.connect():
            return self.summary()

        # Phase 2: Start task and auto-select thinking option
        await self.send("task.start", {"user_input": "Say hello"})

        log("FLOW", "Phase 2: Waiting for thinking node (up to 60s)...")
        thinking_ok = False
        for _ in range(12):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                self.fail("FLOW", "Connection closed during thinking")
                return self.summary()
            msg_type = data.get("type", "")
            if msg_type == "thinking.node_created":
                self.ok("THINKING", "Received thinking.node_created")
                options = data.get("payload", {}).get("options", [])
                option_id = options[0]["id"] if options else "A"
                node_id = data.get("payload", {}).get("node_id", "")
                log("INFO", f"Options: {[o.get('id') for o in options]}, selecting {option_id}")
                await self.send("select_option", {"nodeId": node_id, "optionId": option_id})
                thinking_ok = True
                break
            elif msg_type == "execution.blueprint_loaded":
                log("INFO", "Direct execution without thinking")
                thinking_ok = True
                break

        if not thinking_ok:
            self.fail("THINKING", "Timeout waiting for thinking node")
            return self.summary()

        # Phase 3: Wait for execution step_started
        log("FLOW", "Phase 3: Waiting for execution step (up to 90s)...")
        step_ok = False
        for _ in range(18):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                self.fail("EXECUTION", "Connection closed during execution")
                return self.summary()
            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            if msg_type == "execution.step_started":
                self.step_id = payload.get("step_id", "")
                self.task_id = payload.get("task_id", "")
                step_name = payload.get("name", "")
                self.ok("STEP", f"Step started: {step_name} ({self.step_id})")
                step_ok = True
                break
            elif msg_type == "execution.blueprint_loaded":
                steps = payload.get("steps", [])
                if steps:
                    self.step_id = steps[0].get("id", "")
                    self.task_id = payload.get("task_id", "")
                    self.ok("BLUEPRINT", f"Blueprint loaded, first step: {self.step_id}")
                    step_ok = True
                    break
            elif msg_type == "task.started":
                self.task_id = payload.get("task_id", "")
                log("INFO", f"Task ID: {self.task_id}")

        if not step_ok:
            self.fail("EXECUTION", "Timeout waiting for execution step")
            return self.summary()

        # Phase 4: Send freeze_request
        log("FLOW", "Phase 4: Sending freeze_request...")
        await self.send("freeze_request", {
            "step_id": self.step_id,
            "reason": "E2E verification test",
        })

        freeze_ok = False
        for _ in range(6):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                break
            msg_type = data.get("type", "")
            if msg_type == "freeze.confirmed":
                token = data.get("payload", {}).get("freezeToken", "")
                screenshot = data.get("payload", {}).get("screenshot", "")
                self.ok("FREEZE", f"Received freeze.confirmed (token={token[:16]}..., screenshot={bool(screenshot)})")
                freeze_ok = True
                break
            elif msg_type == "error":
                err_msg = data.get("payload", {}).get("message", "")
                log("INFO", f"Backend error: {err_msg}")
                break
            elif msg_type == "adapter.runtime.frozen":
                self.ok("FREEZE", "Received adapter.runtime.frozen")
                freeze_ok = True
                break

        if not freeze_ok:
            self.fail("FREEZE", "No freeze confirmation received")

        # Phase 5: Send submit_annotation
        log("FLOW", "Phase 5: Sending submit_annotation...")
        await self.send("submit_annotation", {
            "step_id": self.step_id,
            "annotation": "test annotation from E2E",
        })

        unfreeze_ok = False
        for _ in range(6):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                break
            msg_type = data.get("type", "")
            if msg_type in ("status_update", "adapter.runtime.unfrozen", "annotation.submitted"):
                self.ok("UNFREEZE", f"Received {msg_type}")
                unfreeze_ok = True
                break
            elif msg_type == "error":
                err_msg = data.get("payload", {}).get("message", "")
                log("INFO", f"Backend error on unfreeze: {err_msg}")
                break

        if not unfreeze_ok:
            self.fail("UNFREEZE", "No unfreeze confirmation received")

        # Close
        try:
            await self.ws.close()
        except Exception:
            pass

        return self.summary()

    def summary(self):
        print()
        log("SUMMARY", "=" * 60)
        log("SUMMARY", f"PASSED: {self.passed} | FAILED: {self.failed}")
        if self.failed == 0:
            log("SUMMARY", "Intervention chain: ALL GREEN [OK]")
        elif self.failed <= 2:
            log("SUMMARY", "Intervention chain: MOSTLY OK [WARN]")
        else:
            log("SUMMARY", "Intervention chain: ISSUES FOUND [FAIL]")
        log("SUMMARY", "=" * 60)
        return 0 if self.failed == 0 else 1


async def main():
    v = Verifier()
    try:
        code = await v.run()
    except KeyboardInterrupt:
        log("EXIT", "Interrupted by user")
        code = 1
    except Exception as e:
        log("FATAL", f"Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    asyncio.run(main())
