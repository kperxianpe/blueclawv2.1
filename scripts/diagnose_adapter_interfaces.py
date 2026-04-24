#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter Interface Diagnostic Script
Tests all Week 21 adapter WebSocket endpoints and generates a screenshot report.
"""
import os
import sys
import json
import time
import asyncio
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["PYTHONPATH"] = PROJECT_ROOT
sys.path.insert(0, PROJECT_ROOT)

REPORT_DIR = os.path.join(PROJECT_ROOT, "scripts", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT_HTML = os.path.join(REPORT_DIR, f"adapter_interface_report_{TIMESTAMP}.html")
REPORT_PNG = os.path.join(REPORT_DIR, f"adapter_interface_report_{TIMESTAMP}.png")

BACKEND_CMD = [sys.executable, os.path.join(PROJECT_ROOT, "backend", "main.py")]
WS_URL = "ws://localhost:8006"

RESULTS = []
backend_proc = None


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)


def start_backend():
    global backend_proc
    log("Starting backend server...")
    log_file = open(os.path.join(REPORT_DIR, f"backend_{TIMESTAMP}.log"), "w", encoding="utf-8")
    backend_proc = subprocess.Popen(
        BACKEND_CMD,
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": PROJECT_ROOT},
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    backend_proc._log_file = log_file
    return backend_proc


def stop_backend():
    global backend_proc
    if backend_proc:
        log("Stopping backend server...")
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(backend_proc.pid)], capture_output=True)
            else:
                backend_proc.terminate()
                backend_proc.wait(timeout=5)
        except Exception:
            try:
                backend_proc.kill()
            except Exception:
                pass
        if hasattr(backend_proc, '_log_file'):
            try:
                backend_proc._log_file.close()
            except Exception:
                pass
        backend_proc = None


def wait_for_backend(timeout=30):
    log(f"Waiting for backend at {WS_URL}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", 8006))
            s.close()
            log("Backend is ready")
            return True
        except Exception:
            time.sleep(1)
    return False


async def ws_call(msg_type, payload, timeout=10):
    """Send a WebSocket message and wait for response."""
    import websockets
    try:
        async with websockets.connect(WS_URL, open_timeout=5, close_timeout=5) as ws:
            msg = {
                "type": msg_type,
                "payload": payload,
                "timestamp": int(time.time() * 1000),
                "message_id": f"test_{int(time.time()*1000)}"
            }
            await ws.send(json.dumps(msg))
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                return json.loads(raw)
            except asyncio.TimeoutError:
                return {"type": "error", "error": "Timeout waiting for response"}
    except Exception as e:
        return {"type": "error", "error": f"Connection failed: {e}"}


async def run_tests():
    global RESULTS

    # Test 1: adapter.list (no task needed)
    log("Testing adapter.list...")
    resp = await ws_call("adapter.list", {})
    RESULTS.append({
        "name": "adapter.list",
        "sent": {"type": "adapter.list", "payload": {}},
        "received": resp,
        "status": "PASS" if resp.get("type") == "adapter.listed" else "FAIL"
    })

    # Test 2: adapter.create
    log("Testing adapter.create...")
    resp = await ws_call("adapter.create", {"name": "TestAdapter", "type": "single", "icon": "🔧"})
    RESULTS.append({
        "name": "adapter.create",
        "sent": {"type": "adapter.create", "payload": {"name": "TestAdapter", "type": "single"}},
        "received": resp,
        "status": "PASS" if resp.get("type") == "adapter.created" else "FAIL"
    })
    created_id = resp.get("payload", {}).get("id") if resp.get("type") == "adapter.created" else None

    # Test 3: adapter.get (existing)
    log("Testing adapter.get...")
    if created_id:
        resp = await ws_call("adapter.get", {"adapter_id": created_id})
        RESULTS.append({
            "name": "adapter.get (existing)",
            "sent": {"type": "adapter.get", "payload": {"adapter_id": created_id}},
            "received": resp,
            "status": "PASS" if resp.get("type") == "adapter.detail" else "FAIL"
        })
    else:
        RESULTS.append({
            "name": "adapter.get (existing)",
            "sent": {"type": "adapter.get"},
            "received": {"error": "Skipped: no created adapter"},
            "status": "SKIP"
        })

    # Test 4: adapter.get (non-existing)
    log("Testing adapter.get (non-existing)...")
    resp = await ws_call("adapter.get", {"adapter_id": "nonexistent_123"})
    RESULTS.append({
        "name": "adapter.get (non-existing)",
        "sent": {"type": "adapter.get", "payload": {"adapter_id": "nonexistent_123"}},
        "received": resp,
        "status": "PASS" if resp.get("type") == "error" else "FAIL"
    })

    # Test 5: adapter.update
    log("Testing adapter.update...")
    if created_id:
        resp = await ws_call("adapter.update", {"adapter_id": created_id, "updates": {"name": "UpdatedAdapter"}})
        RESULTS.append({
            "name": "adapter.update",
            "sent": {"type": "adapter.update", "payload": {"adapter_id": created_id, "updates": {"name": "UpdatedAdapter"}}},
            "received": resp,
            "status": "PASS" if resp.get("type") == "adapter.updated" else "FAIL"
        })
    else:
        RESULTS.append({
            "name": "adapter.update",
            "sent": {},
            "received": {"error": "Skipped"},
            "status": "SKIP"
        })

    # Test 6: adapter.attach_to_step (no task - should fail or mock)
    log("Testing adapter.attach_to_step...")
    resp = await ws_call("adapter.attach_to_step", {
        "task_id": "test_task_001",
        "step_id": "step_001",
        "adapter_id": created_id or "mock_adapter"
    })
    RESULTS.append({
        "name": "adapter.attach_to_step",
        "sent": {"type": "adapter.attach_to_step", "payload": {"task_id": "test_task_001", "step_id": "step_001"}},
        "received": resp,
        "status": "PASS" if resp.get("type") in ("adapter.attach_success", "adapter.attached") else "FAIL"
    })

    # Test 7: adapter.detach_from_step
    log("Testing adapter.detach_from_step...")
    resp = await ws_call("adapter.detach_from_step", {
        "task_id": "test_task_001",
        "step_id": "step_001",
        "adapter_id": created_id or "mock_adapter"
    })
    RESULTS.append({
        "name": "adapter.detach_from_step",
        "sent": {"type": "adapter.detach_from_step"},
        "received": resp,
        "status": "PASS" if resp.get("type") == "adapter.detached" else "FAIL"
    })

    # Test 8: adapter.enter_edit (blueprint type needed)
    log("Testing adapter.enter_edit...")
    resp = await ws_call("adapter.enter_edit", {"adapter_id": created_id or "mock"})
    RESULTS.append({
        "name": "adapter.enter_edit",
        "sent": {"type": "adapter.enter_edit", "payload": {"adapter_id": created_id or "mock"}},
        "received": resp,
        "status": "INFO"  # May fail if not blueprint type
    })

    # Test 9: adapter.execute
    log("Testing adapter.execute...")
    resp = await ws_call("adapter.execute", {
        "task_id": "test_task_001",
        "adapter_id": created_id or "mock_adapter"
    })
    RESULTS.append({
        "name": "adapter.execute",
        "sent": {"type": "adapter.execute"},
        "received": resp,
        "status": "PASS" if resp.get("type") == "adapter.execution_started" else "FAIL"
    })

    # Test 10: adapter.clone
    log("Testing adapter.clone...")
    if created_id:
        resp = await ws_call("adapter.clone", {"adapter_id": created_id, "new_name": "ClonedAdapter"})
        RESULTS.append({
            "name": "adapter.clone",
            "sent": {"type": "adapter.clone", "payload": {"adapter_id": created_id}},
            "received": resp,
            "status": "PASS" if resp.get("type") == "adapter.cloned" else "FAIL"
        })
    else:
        RESULTS.append({
            "name": "adapter.clone",
            "sent": {},
            "received": {"error": "Skipped"},
            "status": "SKIP"
        })

    # Test 11: adapter.delete
    log("Testing adapter.delete...")
    if created_id:
        resp = await ws_call("adapter.delete", {"adapter_id": created_id})
        RESULTS.append({
            "name": "adapter.delete",
            "sent": {"type": "adapter.delete", "payload": {"adapter_id": created_id}},
            "received": resp,
            "status": "PASS" if resp.get("type") == "adapter.deleted" else "FAIL"
        })
    else:
        RESULTS.append({
            "name": "adapter.delete",
            "sent": {},
            "received": {"error": "Skipped"},
            "status": "SKIP"
        })

    # Week 30.5 new interfaces (expected to fail since backend doesn't implement them yet)
    log("Testing Week 30.5 new interfaces (expected UNKNOWN)...")
    for msg_type in ["adapter.action", "adapter.state_changed", "adapter.annotated", "adapter.frozen", "adapter.unfrozen"]:
        resp = await ws_call(msg_type, {"task_id": "test", "step_id": "s1"})
        RESULTS.append({
            "name": msg_type,
            "sent": {"type": msg_type},
            "received": resp,
            "status": "EXPECTED_FAIL" if "Unknown" in str(resp.get("error", "")) else "UNEXPECTED"
        })


def generate_html():
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    skipped = sum(1 for r in RESULTS if r["status"] in ("SKIP", "INFO"))
    expected_fail = sum(1 for r in RESULTS if r["status"] == "EXPECTED_FAIL")

    rows = ""
    for r in RESULTS:
        status_color = {
            "PASS": "#22c55e",
            "FAIL": "#ef4444",
            "SKIP": "#94a3b8",
            "INFO": "#3b82f6",
            "EXPECTED_FAIL": "#f59e0b",
            "UNEXPECTED": "#dc2626"
        }.get(r["status"], "#94a3b8")

        sent = json.dumps(r["sent"], ensure_ascii=False, indent=2)
        received = json.dumps(r["received"], ensure_ascii=False, indent=2)

        rows += f"""
        <tr>
            <td><strong>{r['name']}</strong></td>
            <td><span class="badge" style="background:{status_color}">{r['status']}</span></td>
            <td><pre>{sent}</pre></td>
            <td><pre>{received}</pre></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Adapter Interface Diagnostic Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #0f172a; color: #e2e8f0; }}
.header {{ text-align: center; padding: 20px; background: #1e293b; border-radius: 12px; margin-bottom: 20px; }}
.header h1 {{ margin: 0; font-size: 24px; }}
.header p {{ margin: 8px 0 0; color: #94a3b8; font-size: 14px; }}
.stats {{ display: flex; gap: 12px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap; }}
.stat {{ background: #1e293b; padding: 16px 24px; border-radius: 10px; text-align: center; min-width: 100px; }}
.stat .num {{ font-size: 28px; font-weight: bold; }}
.stat .label {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }}
th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; }}
th {{ background: #334155; font-weight: 600; font-size: 13px; }}
td {{ font-size: 13px; vertical-align: top; }}
pre {{ background: #0f172a; padding: 8px; border-radius: 6px; overflow-x: auto; font-size: 11px; max-height: 200px; margin: 0; }}
.badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; color: white; }}
.section {{ margin-bottom: 8px; font-size: 16px; font-weight: 600; color: #60a5fa; }}
</style>
</head>
<body>
<div class="header">
    <h1>Adapter Interface Diagnostic Report</h1>
    <p>Generated: {datetime.now().isoformat()} | Backend: {WS_URL}</p>
</div>
<div class="stats">
    <div class="stat"><div class="num" style="color:#22c55e">{passed}</div><div class="label">PASS</div></div>
    <div class="stat"><div class="num" style="color:#ef4444">{failed}</div><div class="label">FAIL</div></div>
    <div class="stat"><div class="num" style="color:#94a3b8">{skipped}</div><div class="label">SKIP/INFO</div></div>
    <div class="stat"><div class="num" style="color:#f59e0b">{expected_fail}</div><div class="label">EXPECTED_FAIL</div></div>
    <div class="stat"><div class="num">{total}</div><div class="label">TOTAL</div></div>
</div>
<div class="section">Detailed Results</div>
<table>
    <thead>
        <tr>
            <th style="width:18%">Interface</th>
            <th style="width:10%">Status</th>
            <th style="width:36%">Request</th>
            <th style="width:36%">Response</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>
</body>
</html>"""

    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"HTML report saved: {REPORT_HTML}")


async def take_screenshot():
    log("Taking screenshot with Playwright...")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1400, "height": 1200})
            await page.goto(f"file:///{REPORT_HTML.replace(os.sep, '/')}")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=REPORT_PNG, full_page=True)
            await browser.close()
        log(f"Screenshot saved: {REPORT_PNG}")
        return True
    except Exception as e:
        log(f"Screenshot failed: {e}")
        return False


async def main():
    global RESULTS
    try:
        start_backend()
        if not wait_for_backend(timeout=30):
            log("Backend failed to start, aborting")
            RESULTS.append({"name": "backend_startup", "status": "FAIL", "sent": {}, "received": {"error": "Backend startup timeout"}})
            return

        # Wait a bit for imports to settle
        time.sleep(2)
        await run_tests()
    finally:
        stop_backend()

    generate_html()
    await take_screenshot()

    # Summary
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    expected_fail = sum(1 for r in RESULTS if r["status"] == "EXPECTED_FAIL")
    log(f"\n{'='*50}")
    log(f"Diagnostic complete: {passed} pass, {failed} fail, {expected_fail} expected_fail / {total} total")
    log(f"Report: {REPORT_HTML}")
    log(f"Screenshot: {REPORT_PNG}")


if __name__ == "__main__":
    asyncio.run(main())
