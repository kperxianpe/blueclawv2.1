#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方向 A：前端 ↔ 后端 E2E 干预链路验证

用法：确保后端已启动 (python backend/main.py) 后运行：
    cd blueclawv2
    python tests/e2e_intervention_verify.py

验证链路：
1. WS 连接
2. task.start → thinking → select_option → execution
3. freeze_request → freeze.confirmed
4. submit_annotation → 恢复执行
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import websockets

WS_URL = "ws://127.0.0.1:8006/ws"
TIMEOUT = 120  # LLM 调用可能较慢


class colors:
    OK = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[94m"
    RESET = "\033[0m"


def log_ok(step, msg):
    print(f"{colors.OK}[PASS]{colors.RESET} {step}: {msg}")


def log_fail(step, msg):
    print(f"{colors.FAIL}[FAIL]{colors.RESET} {step}: {msg}")


def log_info(step, msg):
    print(f"{colors.INFO}[INFO]{colors.RESET} {step}: {msg}")


def log_warn(step, msg):
    print(f"{colors.WARN}[WARN]{colors.RESET} {step}: {msg}")


class InterventionVerifier:
    def __init__(self):
        self.ws = None
        self.task_id = None
        self.step_id = None
        self.freeze_token = None
        self.messages = []
        self.errors = []
        self.passed = 0
        self.failed = 0

    async def connect(self):
        try:
            self.ws = await websockets.connect(WS_URL, ping_interval=20, ping_timeout=10)
            log_ok("CONNECT", f"WebSocket 已连接 {WS_URL}")
            self.passed += 1
            return True
        except Exception as e:
            log_fail("CONNECT", f"无法连接: {e}")
            self.failed += 1
            return False

    async def send(self, msg_type, payload):
        msg = {
            "type": msg_type,
            "payload": payload,
            "message_id": f"test_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
        }
        await self.ws.send(json.dumps(msg))
        log_info("SEND", f"{msg_type} -> {json.dumps(payload, ensure_ascii=False)[:100]}")

    async def recv_with_timeout(self, timeout=30):
        try:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(raw)
            self.messages.append(data)
            log_info("RECV", f"{data.get('type', 'unknown')}: {json.dumps(data.get('payload', {}), ensure_ascii=False)[:120]}")
            return data
        except asyncio.TimeoutError:
            log_warn("RECV", f"等待消息超时 ({timeout}s)")
            return None
        except Exception as e:
            log_fail("RECV", f"接收错误: {e}")
            return None

    async def wait_for_message(self, target_type, timeout=60):
        start = time.time()
        while time.time() - start < timeout:
            data = await self.recv_with_timeout(timeout=5)
            if data and data.get("type") == target_type:
                return data
            if data and data.get("type") == "error":
                log_fail("FLOW", f"收到错误消息: {data}")
                return data
        log_fail("FLOW", f"超时未收到 {target_type}")
        return None

    async def run(self):
        print("=" * 60)
        print("Blueclaw E2E 干预链路验证")
        print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"WS 地址: {WS_URL}")
        print("=" * 60)
        print()

        # Step 1: 连接
        if not await self.connect():
            return

        # Step 2: 发送 task.start
        print("\n--- Phase 1: 任务启动 ---")
        user_input = "打开百度首页，搜索'Blueclaw'并截图"
        await self.send("task.start", {"user_input": user_input})

        # Step 3: 等待 thinking 节点
        print("\n--- Phase 2: 等待 Thinking 节点 ---")
        thinking_msg = await self.wait_for_message("thinking.node_created", timeout=60)
        if thinking_msg:
            log_ok("THINKING", "收到 thinking.node_created")
            self.passed += 1
            # 提取选项
            options = thinking_msg.get("payload", {}).get("options", [])
            if options:
                option_id = options[0].get("id", "A")
                log_info("THINKING", f"选项: {[o.get('id') for o in options]}, 将选择 {option_id}")
            else:
                option_id = "A"
                log_warn("THINKING", "未找到选项，默认选 A")
        else:
            log_fail("THINKING", "未收到 thinking.node_created")
            self.failed += 1
            # 尝试继续：可能没有 thinking 阶段直接进 execution
            option_id = None

        # Step 4: 选择选项
        if option_id:
            print("\n--- Phase 3: 选择选项 ---")
            await self.send("select_option", {
                "nodeId": thinking_msg.get("payload", {}).get("node_id", ""),
                "optionId": option_id,
            })

        # Step 5: 等待 execution blueprint 或 step 消息
        print("\n--- Phase 4: 等待 Execution 阶段 ---")
        exec_msg = await self.wait_for_message("execution.blueprint_loaded", timeout=60)
        if exec_msg:
            log_ok("EXECUTION", "收到 execution.blueprint_loaded")
            self.passed += 1
            steps = exec_msg.get("payload", {}).get("steps", [])
            if steps:
                self.step_id = steps[0].get("id", "step_1")
                self.task_id = exec_msg.get("payload", {}).get("task_id", "")
                log_info("EXECUTION", f"第一步 ID: {self.step_id}, 任务 ID: {self.task_id}")
            else:
                log_warn("EXECUTION", "Blueprint steps 为空，将从 step_started 提取")
        else:
            log_warn("EXECUTION", "未收到 execution.blueprint_loaded，尝试从 step 消息提取")

        # Step 6: 监听 execution.step_started 获取 step_id（适配实际消息格式）
        print("\n--- Phase 5: 监听步骤执行消息 ---")
        step_found = False
        listen_deadline = time.time() + 30
        while time.time() < listen_deadline and not step_found:
            data = await self.recv_with_timeout(timeout=5)
            if not data:
                continue
            msg_type = data.get("type", "")
            payload = data.get("payload", {})
            if msg_type in ("execution.step_started", "step_status_changed"):
                status = payload.get("status", "")
                sid = payload.get("step_id", "")
                if sid and not self.step_id:
                    self.step_id = sid
                    self.task_id = payload.get("task_id", self.task_id or "")
                    log_info("STEP", f"提取到 step_id: {self.step_id}")
                if status == "running":
                    log_ok("STEP", "步骤进入 running 状态")
                    self.passed += 1
                    step_found = True
                elif msg_type == "execution.step_started":
                    log_info("STEP", f"步骤开始: {sid}")
                    step_found = True
            elif msg_type == "execution.step_completed":
                log_info("STEP", f"步骤完成: {payload.get('step_id', '')}")

        if not self.step_id:
            log_fail("STEP", "未能从任何消息中提取 step_id")
            self.failed += 1
            return

        # Step 7: 发送 freeze_request
        print("\n--- Phase 6: 发送 freeze_request ---")
        if self.step_id:
            await self.send("freeze_request", {
                "step_id": self.step_id,
                "reason": "E2E 验证测试：用户请求冻结",
            })
        else:
            log_fail("FREEZE", "缺少 step_id，无法发送 freeze_request")
            self.failed += 1
            return

        # Step 8: 等待 freeze.confirmed
        freeze_msg = await self.wait_for_message("freeze.confirmed", timeout=30)
        if freeze_msg:
            log_ok("FREEZE", "收到 freeze.confirmed")
            self.passed += 1
            self.freeze_token = freeze_msg.get("payload", {}).get("freezeToken", "")
            screenshot = freeze_msg.get("payload", {}).get("screenshot", "")
            log_info("FREEZE", f"freeze_token: {self.freeze_token[:20]}... screenshot: {bool(screenshot)}")
        else:
            log_fail("FREEZE", "未收到 freeze.confirmed")
            self.failed += 1

        # Step 9: 发送 submit_annotation（解冻）
        print("\n--- Phase 7: 发送 submit_annotation（解冻）---")
        await self.send("submit_annotation", {
            "step_id": self.step_id,
            "annotation": "E2E 验证：用户标注测试",
        })

        # Step 10: 等待状态更新
        status_msg = await self.wait_for_message("status_update", timeout=30)
        if status_msg:
            log_ok("UNFREEZE", "收到 status_update（解冻通知）")
            self.passed += 1
        else:
            # 也可能收到 adapter.runtime.unfrozen
            unfrozen_msg = await self.wait_for_message("adapter.runtime.unfrozen", timeout=10)
            if unfrozen_msg:
                log_ok("UNFREEZE", "收到 adapter.runtime.unfrozen")
                self.passed += 1
            else:
                log_warn("UNFREEZE", "未收到明确解冻通知（可能通过其他消息推送）")

        # Step 11: 关闭
        await self.ws.close()
        print("\n" + "=" * 60)
        print("验证完成")
        print(f"通过: {self.passed} | 失败: {self.failed}")
        if self.failed == 0:
            print(f"{colors.OK}干预链路全部打通 ✅{colors.RESET}")
        elif self.failed <= 2:
            print(f"{colors.WARN}干预链路基本打通，部分环节需关注 ⚠️{colors.RESET}")
        else:
            print(f"{colors.FAIL}干预链路存在严重问题 ❌{colors.RESET}")
        print("=" * 60)


async def main():
    verifier = InterventionVerifier()
    try:
        await verifier.run()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        log_fail("FATAL", f"未捕获异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
