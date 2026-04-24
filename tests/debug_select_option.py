#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import websockets

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS_URL = "ws://127.0.0.1:8006/ws"

async def test():
    ws = await websockets.connect(WS_URL)
    await ws.send(json.dumps({
        "type": "task.start",
        "payload": {"user_input": "搜索百度和阿里巴巴AI技术"},
        "message_id": "test_1",
        "timestamp": 1
    }))
    
    task_id = None
    node_id = None
    
    while True:
        msg = json.loads(await ws.recv())
        t = msg["type"]
        print(f"RECV: {t}")
        
        if t == "error":
            print(f"  ERROR payload: {msg.get('payload', {})}")
        
        if t == "thinking.node_created":
            node_id = msg["payload"]["node"]["id"]
            task_id = msg["payload"]["node"].get("task_id", "")
            options = msg["payload"].get("options", [])
            print(f"  node_id={node_id}, task_id={task_id}, options={len(options)}")
            if options:
                opt_id = options[0]["id"]
                payload = {
                    "nodeId": node_id,
                    "optionId": opt_id,
                }
                print(f"  SENDING select_option: {payload}")
                await ws.send(json.dumps({
                    "type": "select_option",
                    "payload": payload,
                    "message_id": "test_2",
                    "timestamp": 2
                }))
        
        if t == "execution.blueprint_loaded":
            print("GOT BLUEPRINT!")
            break
            
        if t == "thinking.completed":
            print("Thinking completed, waiting for blueprint...")
    
    await ws.close()

asyncio.run(test())
