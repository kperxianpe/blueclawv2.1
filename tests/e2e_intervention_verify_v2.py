#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方向 A：前端 <-> 后端 E2E 干预链路验证（V2 修复版）
用法：确保后端已启动后运行：
    cd blueclawv2
    python tests/e2e_intervention_verify_v2.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import websockets

WS_URL = "ws://127.0.0.1:8006/ws"
RECV_TIMEOUT = 45


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

    def ok(self, step, msg):
        self.passed += 1
        log("OK", f"{step}: {msg}")

    def fail(self, step, msg):
        self.failed += 1
        log("FAIL", f"{step}: {msg}")

    async def connect(self):
        try:
            self.ws = await websockets.connect(WS_URL, ping_interval=20, ping_timeout=10)
            self.ok("CONNECT", f"WebSocket connected {WS_URL}")
            return True
        except Exception as e:
            self.fail("CONNECT", f"Cannot connect: {e}")
            return False

    async def send(self, msg_type, payload):
        msg = {
            "type": msg_type,
            "payload": payload,
            "message_id": f"test_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
        }
        await self.ws.send(json.dumps(msg))
        log("SEND", msg_type)

    async def recv_one(self, timeout=RECV_TIMEOUT):
        try:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(raw)
            log("RECV", data.get("type", "unknown"))
            return data
        except asyncio.TimeoutError:
            return None
        except websockets.exceptions.ConnectionClosed as e:
            log("CLOSED", f"Connection closed: {e}")
            return {"_closed": True}
        except Exception as e:
            log("ERROR", f"Recv error: {e}")
            return None

    async def run(self):
        log("START", "=" * 50)
        log("START", "Blueclaw E2E Intervention Link Verification")
        log("START", f"WS: {WS_URL}")

        # 1. Connect
        if not await self.connect():
            return self.summary()

        # 2. Start task
        await self.send("task.start", {"user_input": "Open baidu.com"})

        # 3. Wait for thinking node and select option
        log("FLOW", "Waiting for thinking node...")
        thinking_data = None
        deadline = time.time() + 60
        while time.time() < deadline:
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                self.fail("FLOW", "Connection closed during thinking")
                return self.summary()
            msg_type = data.get("type", "")
            if msg_type == "thinking.node_created":
                thinking_data = data
                self.ok("THINKING", "Received thinking.node_created")
                options = data.get("payload", {}).get("options", [])
                option_id = options[0]["id"] if options else "A"
                log("INFO", f"Options: {[o.get('id') for o in options]}, selecting {option_id}")
                await self.send("select_option", {
                    "nodeId": data.get("payload", {}).get("node_id", ""),
                    "optionId": option_id,
                })
                break
            elif msg_type == "execution.blueprint_loaded":
                log("INFO", "Skipped thinking, direct execution")
                break

        if not thinking_data and time.time() >= deadline:
            self.fail("THINKING", "Timeout waiting for thinking.node_created")
            return self.summary()

        # 4. Wait for execution phase
        log("FLOW", "Waiting for execution phase...")
        execution_data = None
        step_started_msgs = []
        deadline = time.time() + 60
        while time.time() < deadline:
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                self.fail("EXECUTION", "Connection closed during execution")
                return self.summary()
            msg_type = data.get("type", "")
            if msg_type == "execution.blueprint_loaded":
                execution_data = data
                self.ok("EXECUTION", "Received execution.blueprint_loaded")
                steps = data.get("payload", {}).get("steps", [])
                if steps:
                    self.step_id = steps[0].get("id", "")
                    self.task_id = data.get("payload", {}).get("task_id", "")
                    log("INFO", f"Step ID: {self.step_id}, Task ID: {self.task_id}")
                break
            elif msg_type == "execution.step_started":
                step_started_msgs.append(data)
                self.step_id = data.get("payload", {}).get("step_id", "")
                self.task_id = data.get("payload", {}).get("task_id", "")
                log("INFO", f"Step started: {self.step_id}")
                # Don't break, wait for blueprint_loaded
            elif msg_type == "task.started":
                self.task_id = data.get("payload", {}).get("task_id", "")
                log("INFO", f"Task started: {self.task_id}")

        if not execution_data and not step_started_msgs:
            self.fail("EXECUTION", "No execution messages received")
            return self.summary()

        if step_started_msgs and not self.step_id:
            self.step_id = step_started_msgs[0].get("payload", {}).get("step_id", "")
            self.ok("STEP_ID", f"Extracted from step_started: {self.step_id}")
        elif self.step_id:
            self.ok("STEP_ID", f"Available: {self.step_id}")
        else:
            self.fail("STEP_ID", "Cannot extract step_id")
            return self.summary()

        # Reconnect if needed
        if self.ws.close_code is not None:
            log("INFO", "Reconnecting...")
            if not await self.connect():
                return self.summary()

        # 5. Send freeze_request
        log("FLOW", "Sending freeze_request...")
        await self.send("freeze_request", {
            "step_id": self.step_id,
            "reason": "E2E test freeze",
        })

        freeze_msg = None
        deadline = time.time() + 30
        while time.time() < deadline:
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                break
            if data.get("type") == "freeze.confirmed":
                freeze_msg = data
                break

        if freeze_msg:
            self.ok("FREEZE", "Received freeze.confirmed")
            token = freeze_msg.get("payload", {}).get("freezeToken", "")
            screenshot = freeze_msg.get("payload", {}).get("screenshot", "")
            log("INFO", f"freeze_token: {token[:20]}..., screenshot: {bool(screenshot)}")
        else:
            self.fail("FREEZE", "No freeze.confirmed received")

        # 6. Send submit_annotation
        log("FLOW", "Sending submit_annotation...")
        await self.send("submit_annotation", {
            "step_id": self.step_id,
            "annotation": "test annotation",
        })

        unfreeze_ok = False
        deadline = time.time() + 20
        while time.time() < deadline:
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                break
            msg_type = data.get("type", "")
            if msg_type in ("status_update", "adapter.runtime.unfrozen"):
                unfreeze_ok = True
                break

        if unfreeze_ok:
            self.ok("UNFREEZE", "Received unfreeze notification")
        else:
            self.fail("UNFREEZE", "No unfreeze notification received")

        # Close
        try:
            await self.ws.close()
        except Exception:
            pass

        return self.summary()

    def summary(self):
        print()
        log("SUMMARY", "=" * 50)
        log("SUMMARY", f"PASSED: {self.passed} | FAILED: {self.failed}")
        if self.failed == 0:
            log("SUMMARY", "Intervention chain fully working [OK]")
        elif self.failed <= 2:
            log("SUMMARY", "Intervention chain mostly working [WARN]")
        else:
            log("SUMMARY", "Intervention chain has issues [FAIL]")
        return 0 if self.failed == 0 else 1


async def main():
    v = Verifier()
    try:
        code = await v.run()
    except KeyboardInterrupt:
        log("EXIT", "Interrupted")
        code = 1
    except Exception as e:
        log("FATAL", f"Exception: {e}")
        import traceback
        traceback.print_exc()
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    asyncio.run(main())
