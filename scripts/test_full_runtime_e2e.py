#!/usr/bin/env python3
"""Full E2E diagnostic for all adapter runtime message types."""
import asyncio
import sys
sys.path.insert(0, r"C:\Users\10508\My project (1)\forkimi\buleclawv1\blueclawv2")

from backend.websocket.message_router import router
from backend.core.adapter_runtime_manager import adapter_runtime_manager


class MockWebSocket:
    def __init__(self):
        self.sent = []
    async def send_text(self, text):
        self.sent.append(text)


class MockServer:
    def __init__(self):
        self.broadcasts = []
    async def broadcast_to_task(self, task_id, msg):
        self.broadcasts.append((task_id, msg))
    async def send_to_connection(self, ws, msg):
        pass


async def main():
    ws = MockWebSocket()
    server = MockServer()

    # Setup: attach a blueprint
    await router.route(ws, {
        "type": "adapter.blueprint.attach",
        "payload": {"task_id": "t1", "blueprint_id": "bp1", "studio_id": "s1", "adapter_type": "web"},
        "message_id": "m0",
    }, server)

    tests = [
        ("adapter.runtime.start",   {"blueprint_id": "bp1"},               "running"),
        ("adapter.runtime.pause",   {"blueprint_id": "bp1"},               "paused"),
        ("adapter.runtime.resume",  {"blueprint_id": "bp1"},               "running"),
        ("adapter.runtime.freeze",  {"blueprint_id": "bp1", "reason": "r"}, "frozen"),
        ("adapter.runtime.unfreeze",{"blueprint_id": "bp1"},               "running"),
    ]

    all_ok = True
    for msg_type, payload, expected_state in tests:
        resp = await router.route(ws, {
            "type": msg_type,
            "payload": payload,
            "message_id": f"test_{msg_type}",
        }, server)
        actual = resp.get("payload", {}).get("state")
        ok = actual == expected_state
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {msg_type}: expected={expected_state} actual={actual}")
        if not ok:
            all_ok = False

    # Test retry / replan / dismiss_annotation (these return ack, not state)
    for msg_type in ["adapter.runtime.retry", "adapter.runtime.replan"]:
        resp = await router.route(ws, {
            "type": msg_type,
            "payload": {"blueprint_id": "bp1", "reason": "test"},
            "message_id": f"test_{msg_type}",
        }, server)
        ok = "error" not in resp.get("type", "")
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {msg_type}: type={resp.get('type')}")
        if not ok:
            all_ok = False

    resp = await router.route(ws, {
        "type": "adapter.runtime.dismiss_annotation",
        "payload": {"blueprint_id": "bp1", "annotation_id": "ann_x"},
        "message_id": "test_dismiss",
    }, server)
    ok = resp.get("type") == "adapter.runtime.annotation_dismissed"
    status = "OK" if ok else "FAIL"
    print(f"[{status}] adapter.runtime.dismiss_annotation: type={resp.get('type')}")
    if not ok:
        all_ok = False

    # Test old adapter.action is UNKNOWN (should fail gracefully)
    resp = await router.route(ws, {
        "type": "adapter.action",
        "payload": {"task_id": "t1", "step_id": "bp1", "action": "freeze"},
        "message_id": "test_old_action",
    }, server)
    ok = resp.get("type") == "error"
    status = "OK" if ok else "FAIL"
    print(f"[{status}] adapter.action (old): type={resp.get('type')} (expected error)")
    if not ok:
        all_ok = False

    print()
    if all_ok:
        print("All runtime E2E diagnostics PASSED!")
    else:
        print("Some diagnostics FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
