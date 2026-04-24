#!/usr/bin/env python3
"""Quick E2E diagnostic for adapter runtime handlers."""
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

    # 1. Test adapter.blueprint.attach
    msg = {
        "type": "adapter.blueprint.attach",
        "payload": {
            "task_id": "task_123",
            "blueprint_id": "bp_456",
            "studio_id": "studio_789",
            "adapter_type": "web",
        },
        "message_id": "msg_1",
    }
    resp = await router.route(ws, msg, server)
    print(f"[attach] type={resp.get('type')} payload={resp.get('payload')}")
    assert resp["type"] == "adapter.blueprint.attach_success"

    # 2. Test adapter.runtime.start
    msg = {
        "type": "adapter.runtime.start",
        "payload": {"blueprint_id": "bp_456"},
        "message_id": "msg_2",
    }
    resp = await router.route(ws, msg, server)
    print(f"[start] type={resp.get('type')} state={resp.get('payload',{}).get('state')}")
    assert resp["payload"]["state"] == "running"

    # 3. Test adapter.runtime.freeze
    msg = {
        "type": "adapter.runtime.freeze",
        "payload": {"blueprint_id": "bp_456", "reason": "Test freeze"},
        "message_id": "msg_3",
    }
    resp = await router.route(ws, msg, server)
    print(f"[freeze] type={resp.get('type')} state={resp.get('payload',{}).get('state')}")
    assert resp["payload"]["state"] == "frozen"

    # 4. Test adapter.runtime.unfreeze
    msg = {
        "type": "adapter.runtime.unfreeze",
        "payload": {"blueprint_id": "bp_456"},
        "message_id": "msg_4",
    }
    resp = await router.route(ws, msg, server)
    print(f"[unfreeze] type={resp.get('type')} state={resp.get('payload',{}).get('state')}")
    assert resp["payload"]["state"] == "running"

    # 5. Test adapter.runtime.dismiss_annotation
    msg = {
        "type": "adapter.runtime.dismiss_annotation",
        "payload": {"blueprint_id": "bp_456", "annotation_id": "ann_001"},
        "message_id": "msg_5",
    }
    resp = await router.route(ws, msg, server)
    print(f"[dismiss] type={resp.get('type')} payload={resp.get('payload')}")

    # 6. Test adapter.blueprint.detach
    msg = {
        "type": "adapter.blueprint.detach",
        "payload": {"blueprint_id": "bp_456"},
        "message_id": "msg_6",
    }
    resp = await router.route(ws, msg, server)
    print(f"[detach] type={resp.get('type')} payload={resp.get('payload')}")
    assert resp["type"] == "adapter.blueprint.detach_success"

    print("\nAll E2E diagnostics passed!")


if __name__ == "__main__":
    asyncio.run(main())
