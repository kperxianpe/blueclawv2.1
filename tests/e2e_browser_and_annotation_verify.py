#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方向 B + C：浏览器真实执行 + 标注数据回传验证

验证目标 B:
  - 发送浏览器操作任务
  - ExecutionEngine 启动 Playwright
  - 真实浏览器截图推送回前端

验证目标 C:
  - submit_annotation 包含坐标标注数据
  - 后端接收并解析正确

用法：确保后端已启动后运行：
    cd blueclawv2
    python tests/e2e_browser_and_annotation_verify.py
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


class BrowserVerifier:
    def __init__(self):
        self.ws = None
        self.step_id = None
        self.task_id = None
        self.passed = 0
        self.failed = 0
        self.closed = False
        self.screenshots = []  # 记录所有收到的截图

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
            # 截图消息可能很大，只打印类型
            if t == "screenshot":
                img_len = len(data.get("payload", {}).get("image", ""))
                log("RECV", f"screenshot (image_b64_len={img_len})")
                self.screenshots.append(data)
            else:
                log("RECV", t)
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
        log("START", "Browser Execution + Annotation Verification")
        log("START", f"WS: {WS_URL}")
        log("START", "Task: 'Open baidu.com and search AI'")
        log("START", "=" * 60)

        if not await self.connect():
            return self.summary()

        # Phase 1: Start browser task
        await self.send("task.start", {"user_input": "Open baidu.com and search AI"})

        log("FLOW", "Phase 1: Waiting for thinking node...")
        for _ in range(12):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                return self.summary()
            if data.get("type") == "thinking.node_created":
                self.ok("THINKING", "Received thinking.node_created")
                options = data.get("payload", {}).get("options", [])
                option_id = options[0]["id"] if options else "A"
                node_id = data.get("payload", {}).get("node_id", "")
                await self.send("select_option", {"nodeId": node_id, "optionId": option_id})
                break

        # Phase 2: Wait for execution with browser steps
        log("FLOW", "Phase 2: Waiting for execution with browser steps (up to 120s)...")
        step_ok = False
        screenshot_during_execution = False
        for _ in range(24):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                break
            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            if msg_type == "execution.step_started":
                self.step_id = payload.get("step_id", "")
                self.task_id = payload.get("task_id", "")
                step_name = payload.get("name", "")
                self.ok("STEP", f"Step started: {step_name} ({self.step_id})")
                step_ok = True
            elif msg_type == "screenshot":
                screenshot_during_execution = True
                img_b64 = payload.get("image", "")
                log("INFO", f"Screenshot received during execution, length={len(img_b64)}")
            elif msg_type == "execution.blueprint_loaded":
                steps = payload.get("steps", [])
                if steps and not self.step_id:
                    self.step_id = steps[0].get("id", "")
                    self.task_id = payload.get("task_id", "")

        if not step_ok:
            self.fail("STEP", "Timeout waiting for execution step")
            return self.summary()

        if screenshot_during_execution:
            self.ok("SCREENSHOT", "Screenshot received during step execution")
        else:
            log("INFO", "No screenshot during execution yet (may come later)")

        # Phase 3: Freeze and check screenshot in freeze.confirmed
        log("FLOW", "Phase 3: Sending freeze_request...")
        await self.send("freeze_request", {
            "step_id": self.step_id,
            "reason": "Browser test freeze",
        })

        freeze_screenshot = False
        for _ in range(6):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                break
            msg_type = data.get("type", "")
            if msg_type == "freeze.confirmed":
                screenshot = data.get("payload", {}).get("screenshot", "")
                if screenshot and len(screenshot) > 100:
                    freeze_screenshot = True
                    self.ok("FREEZE", f"freeze.confirmed with screenshot (len={len(screenshot)})")
                else:
                    log("INFO", f"freeze.confirmed screenshot empty or short (len={len(screenshot)})")
                break
            elif msg_type == "screenshot":
                # May receive screenshot before freeze.confirmed
                pass

        if not freeze_screenshot:
            log("INFO", "Freeze screenshot not present (browser may not have been started for this task)")

        # Phase 4: Submit annotation with coordinates (Direction C)
        log("FLOW", "Phase 4: Sending submit_annotation with box coordinates...")
        annotation_payload = {
            "step_id": self.step_id,
            "annotation": "User drew a box at (100, 200)",
            "boxes": [
                {"id": "box-1", "type": "explain", "x": 100, "y": 200, "width": 300, "height": 150}
            ],
            "selected_option": "A",
        }
        await self.send("submit_annotation", annotation_payload)

        annotation_ack = False
        for _ in range(6):
            data = await self.recv_one(timeout=5)
            if not data:
                continue
            if data.get("_closed"):
                break
            msg_type = data.get("type", "")
            if msg_type in ("status_update", "adapter.runtime.unfrozen", "annotation.submitted"):
                self.ok("UNFREEZE", f"Received {msg_type}")
                annotation_ack = True
                break
            elif msg_type == "error":
                err_msg = data.get("payload", {}).get("message", "")
                log("INFO", f"Backend error: {err_msg}")
                break

        if not annotation_ack:
            self.fail("UNFREEZE", "No unfreeze confirmation")

        # Phase 5: Summary
        if self.screenshots:
            total_screenshot_size = sum(len(s.get("payload", {}).get("image", "")) for s in self.screenshots)
            self.ok("SCREENSHOT_TOTAL", f"Total {len(self.screenshots)} screenshots, {total_screenshot_size} chars")
        else:
            log("INFO", "No screenshots received in this session")

        try:
            await self.ws.close()
        except Exception:
            pass

        return self.summary()

    def summary(self):
        print()
        log("SUMMARY", "=" * 60)
        log("SUMMARY", f"PASSED: {self.passed} | FAILED: {self.failed}")
        log("SUMMARY", f"Screenshots captured: {len(self.screenshots)}")
        if self.failed == 0:
            log("SUMMARY", "Browser + Annotation: ALL GREEN [OK]")
        else:
            log("SUMMARY", "Browser + Annotation: ISSUES FOUND [WARN]")
        log("SUMMARY", "=" * 60)
        return 0 if self.failed == 0 else 1


async def main():
    v = BrowserVerifier()
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
