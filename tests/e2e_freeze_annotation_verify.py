#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W2.5 + W3：FreezeOverlay 标注回传全链路验证

验证目标:
  1. 前端发送 freeze_request，后端返回 freeze.confirmed（含 screenshot）
  2. 前端发送 submit_annotation（含 boxes 数组），后端保存并回传
  3. 后端 adapter_runtime_manager 中生成对应 annotation

用法：确保后端已启动后运行：
    cd blueclawv2
    python tests/e2e_freeze_annotation_verify.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import websockets

WS_URL = "ws://127.0.0.1:8006/ws"

# 修复 Windows GBK 编码
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log(tag, msg):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] [{tag}] {msg}")


class FreezeAnnotationVerifier:
    def __init__(self):
        self.ws = None
        self.step_id = None
        self.task_id = None
        self.passed = 0
        self.failed = 0
        self.closed = False
        self.screenshots = []
        self.freeze_token = None

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
            if t == "screenshot":
                img_len = len(data.get("payload", {}).get("image", ""))
                log("RECV", f"screenshot (image_b64_len={img_len})")
                self.screenshots.append(data)
            elif t == "freeze.confirmed":
                sc = len(data.get("payload", {}).get("screenshot", ""))
                log("RECV", f"freeze.confirmed (screenshot_len={sc})")
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

    async def recv_until(self, target_type, timeout=60, skip_types=None):
        skip_types = skip_types or []
        start = time.time()
        while time.time() - start < timeout:
            msg = await self.recv_one(timeout=max(1, timeout - (time.time() - start)))
            if msg is None:
                continue
            if msg.get("_closed"):
                return None
            t = msg.get("type", "")
            if t == target_type:
                return msg
            if t in skip_types:
                continue
        return None

    async def recv_any_of(self, target_types, timeout=60):
        start = time.time()
        while time.time() - start < timeout:
            msg = await self.recv_one(timeout=max(1, timeout - (time.time() - start)))
            if msg is None:
                continue
            if msg.get("_closed"):
                return None
            t = msg.get("type", "")
            if t in target_types:
                return msg
        return None

    async def run(self):
        # Phase 1: Connect
        if not await self.connect():
            return

        # Phase 2: Start task
        user_input = (
            "请帮我搜索一下百度公司的最新信息，"
            "并搜索一下阿里巴巴公司的最新信息，"
            "然后对比一下这两家公司的AI技术发展"
        )
        await self.send("task.start", {"user_input": user_input})

        # Wait for thinking.node_created
        msg = await self.recv_until("thinking.node_created", timeout=30)
        if msg and msg.get("type") == "thinking.node_created":
            self.ok("THINKING", "Received thinking.node_created")
        else:
            self.fail("THINKING", "No thinking.node_created received")
            return

        # Phase 3: Select option to trigger execution
        node_id = msg["payload"]["node"]["id"]
        options = msg["payload"].get("options", [])
        if options:
            option_id = options[0]["id"]
            await self.send("select_option", {
                "nodeId": node_id,
                "optionId": option_id,
            })

        # Wait for task.started to get task_id
        task_started_msg = await self.recv_until("task.started", timeout=30, skip_types=["thinking.option_selected", "thinking.converged"])
        if task_started_msg:
            self.task_id = task_started_msg.get("payload", {}).get("task_id", "")
            self.ok("TASK", f"Task started: {self.task_id}")
        
        # Wait for blueprint
        msg = await self.recv_any_of(["execution.blueprint_loaded", "thinking.completed"], timeout=60)
        if msg and msg.get("type") == "execution.blueprint_loaded":
            self.ok("BLUEPRINT", "Execution blueprint loaded")
        elif msg and msg.get("type") == "thinking.completed":
            # 继续等待 blueprint
            msg = await self.recv_until("execution.blueprint_loaded", timeout=60)
            if msg:
                self.ok("BLUEPRINT", "Execution blueprint loaded (after thinking.completed)")
            else:
                self.fail("BLUEPRINT", "No blueprint loaded")
                return
        else:
            self.fail("BLUEPRINT", "No blueprint loaded")
            return

        # Phase 4: Wait for step execution and capture step_id
        msg = await self.recv_until("execution.step_started", timeout=60, skip_types=["screenshot"])
        if msg and msg.get("type") == "execution.step_started":
            self.step_id = msg["payload"]["step_id"]
            # 如果之前没有获取到 task_id，尝试从这里获取
            if not self.task_id:
                self.task_id = msg["payload"].get("task_id", "")
            self.ok("STEP", f"Step started: {msg['payload'].get('name', self.step_id)}")
        else:
            self.fail("STEP", "No step started")
            return

        # Phase 5: Send freeze_request
        if not self.task_id or not self.step_id:
            self.fail("FREEZE", "Missing task_id or step_id")
            return

        await self.send("freeze_request", {
            "task_id": self.task_id,
            "step_id": self.step_id,
            "reason": "E2E 测试：验证标注回传",
        })

        # Wait for freeze.confirmed
        msg = await self.recv_until("freeze.confirmed", timeout=30)
        if msg and msg.get("type") == "freeze.confirmed":
            payload = msg.get("payload", {})
            screenshot_b64 = payload.get("screenshot", "")
            self.freeze_token = payload.get("freezeToken", "")
            has_screenshot = len(screenshot_b64) > 1000
            self.ok("FREEZE", f"freeze.confirmed received (screenshot={'present' if has_screenshot else 'empty'}, token={'yes' if self.freeze_token else 'no'})")
        else:
            self.fail("FREEZE", "No freeze.confirmed received")
            return

        # Phase 6: Submit annotation with boxes
        test_boxes = [
            {"x": 100, "y": 200, "w": 300, "h": 150, "label": "测试框A"},
            {"x": 500, "y": 100, "w": 200, "h": 200, "label": "测试框B"},
        ]
        await self.send("submit_annotation", {
            "task_id": self.task_id,
            "step_id": self.step_id,
            "annotation": "E2E 测试文本标注",
            "boxes": test_boxes,
            "freeze_token": self.freeze_token,
        })

        # Wait for annotation.submitted 和 status_update（顺序不确定）
        annotation_ok = False
        resume_ok = False
        for _ in range(12):  # 最多等待 60 秒
            msg = await self.recv_one(timeout=5)
            if not msg or msg.get("_closed"):
                break
            t = msg.get("type", "")
            if t == "annotation.submitted":
                payload = msg.get("payload", {})
                returned_boxes = payload.get("boxes", [])
                if len(returned_boxes) == len(test_boxes):
                    self.ok("ANNOTATION", f"annotation.submitted with {len(returned_boxes)} boxes returned")
                else:
                    self.fail("ANNOTATION", f"Expected {len(test_boxes)} boxes, got {len(returned_boxes)}")
                annotation_ok = True
            elif t == "status_update":
                status = msg.get("payload", {}).get("status", "")
                if status == "resumed":
                    self.ok("RESUME", "status_update 'resumed' received")
                    resume_ok = True
                else:
                    log("INFO", f"status_update: {status}")
            elif t in ("screenshot", "execution.step_started", "execution.step_completed"):
                continue  # 忽略执行中的常规消息
            
            if annotation_ok and resume_ok:
                break
        
        if not annotation_ok:
            self.fail("ANNOTATION", "No annotation.submitted received")
        if not resume_ok:
            self.fail("RESUME", "No status_update 'resumed' received")

        # Phase 7: Summary
        total_screenshots = sum(len(s.get("payload", {}).get("image", "")) for s in self.screenshots)
        self.ok("SCREENSHOT_TOTAL", f"Total {len(self.screenshots)} screenshots, {total_screenshots} chars")

        await self.ws.close()
        log("RESULT", f"PASSED: {self.passed} | FAILED: {self.failed}")
        return self.failed == 0


async def main():
    verifier = FreezeAnnotationVerifier()
    success = await verifier.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
