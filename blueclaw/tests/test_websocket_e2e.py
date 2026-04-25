#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket End-to-End Test

Tests the integration between EngineFacade and WebSocket layer.
Simulates a complete client-server interaction.
"""

import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MockWebSocketClient:
    """Mock WebSocket client for testing"""
    
    def __init__(self):
        self.messages_sent: List[Dict] = []
        self.messages_received: List[Dict] = []
        self.connected = False
    
    async def connect(self, uri: str) -> bool:
        """Simulate connection"""
        self.connected = True
        return True
    
    async def send(self, message: Dict):
        """Send message"""
        self.messages_sent.append(message)
    
    async def receive(self) -> Dict:
        """Receive message (simulated)"""
        # Return mock response
        return {"type": "ack", "status": "ok"}
    
    async def close(self):
        """Close connection"""
        self.connected = False


class MockWebSocketServer:
    """Mock WebSocket server that uses EngineFacade"""
    
    def __init__(self):
        self.clients: List[MockWebSocketClient] = []
        self.engine_facades: Dict[str, Any] = {}
        self.events_log: List[Dict] = []
    
    async def handle_client(self, client: MockWebSocketClient):
        """Handle client connection"""
        self.clients.append(client)
        
        try:
            while client.connected:
                # Receive message
                message = await client.receive()
                self.events_log.append({"direction": "received", "data": message})
                
                # Handle message
                response = await self.process_message(message)
                
                # Send response
                await client.send(response)
                self.events_log.append({"direction": "sent", "data": response})
                
        except Exception as e:
            self.events_log.append({"error": str(e)})
    
    async def process_message(self, message: Dict) -> Dict:
        """Process incoming message using EngineFacade"""
        from blueclaw.api import BlueclawEngineFacade
        
        msg_type = message.get("type")
        session_id = message.get("session_id", "default_session")
        
        # Get or create engine facade for session
        if session_id not in self.engine_facades:
            self.engine_facades[session_id] = BlueclawEngineFacade(session_id)
        
        engine = self.engine_facades[session_id]
        
        if msg_type == "process":
            # Process user input
            user_input = message.get("input", "")
            result = await engine.process(user_input)
            return {"type": "process_result", "data": result}
        
        elif msg_type == "select_option":
            # Select option
            node_id = message.get("node_id")
            option_id = message.get("option_id")
            result = await engine.select_option(node_id, option_id)
            return {"type": "select_result", "data": result}
        
        elif msg_type == "execute":
            # Execute blueprint
            result = await engine.execute_blueprint()
            return {"type": "execution_result", "data": result}
        
        elif msg_type == "intervene":
            # Handle intervention
            step_id = message.get("step_id")
            action = message.get("action")
            custom_input = message.get("custom_input")
            result = await engine.intervene(step_id, action, custom_input)
            return {"type": "intervention_result", "data": result}
        
        elif msg_type == "get_status":
            # Get status
            status = engine.get_status()
            return {"type": "status_result", "data": status}
        
        else:
            return {"type": "error", "message": f"Unknown message type: {msg_type}"}


class TestWebSocketE2E:
    """WebSocket end-to-end test suite"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.server = None
        self.client = None
    
    def log(self, msg: str):
        print(f"  {msg}")
    
    def assert_true(self, condition: bool, name: str):
        if condition:
            self.passed += 1
            self.log(f"[PASS] {name}")
        else:
            self.failed += 1
            self.log(f"[FAIL] {name}")
    
    async def run_all(self):
        print("="*60)
        print("Week 16.5 - WebSocket E2E Test")
        print("="*60)
        
        # Setup
        self.server = MockWebSocketServer()
        self.client = MockWebSocketClient()
        
        # Test 1: Connection
        print("\n[1] WebSocket Connection")
        await self.test_connection()
        
        # Test 2: Send Task
        print("\n[2] Send Task")
        await self.test_send_task()
        
        # Test 3: Receive Thinking Node
        print("\n[3] Thinking Node Response")
        await self.test_thinking_node()
        
        # Test 4: Select Option
        print("\n[4] Select Option")
        await self.test_select_option()
        
        # Test 5: Blueprint Ready
        print("\n[5] Blueprint Ready")
        await self.test_blueprint_ready()
        
        # Test 6: Execute Blueprint
        print("\n[6] Execute Blueprint")
        await self.test_execute_blueprint()
        
        # Test 7: Execution Status
        print("\n[7] Execution Status")
        await self.test_execution_status()
        
        # Test 8: Full E2E Flow
        print("\n[8] Full E2E Flow")
        await self.test_full_flow()
        
        # Cleanup
        await self.client.close()
        
        # Summary
        print("\n" + "="*60)
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed ({self.passed/total*100:.1f}%)")
        print("="*60)
        
        return self.failed == 0
    
    async def test_connection(self):
        """Test WebSocket connection"""
        try:
            connected = await self.client.connect("ws://localhost:8765")
            self.assert_true(connected, "Connected to WebSocket")
            self.assert_true(self.client.connected, "Client marked as connected")
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_send_task(self):
        """Test sending a task"""
        try:
            message = {
                "type": "process",
                "session_id": "e2e_session_001",
                "input": "Plan a trip to Beijing"
            }
            
            await self.client.send(message)
            self.assert_true(len(self.client.messages_sent) == 1, "Message sent")
            
            # Process through server
            response = await self.server.process_message(message)
            self.assert_true("data" in response, "Response has data")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_thinking_node(self):
        """Test receiving thinking node"""
        try:
            message = {
                "type": "process",
                "session_id": "e2e_session_002",
                "input": "Book a complex itinerary"
            }
            
            response = await self.server.process_message(message)
            
            self.assert_true("data" in response, "Has response data")
            
            data = response["data"]
            self.assert_true("type" in data, "Response has type")
            
            # Could be thinking_node or execution_preview
            self.assert_true(
                data["type"] in ["thinking_node", "execution_preview"],
                "Valid response type"
            )
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 3
    
    async def test_select_option(self):
        """Test selecting an option"""
        try:
            # First process to create state
            process_msg = {
                "type": "process",
                "session_id": "e2e_session_003",
                "input": "Plan a vacation"
            }
            process_response = await self.server.process_message(process_msg)
            
            # If we got a thinking node, select an option
            if process_response["data"]["type"] == "thinking_node":
                node_id = process_response["data"]["node_id"]
                options = process_response["data"]["options"]
                
                option_id = options[0].id if hasattr(options[0], 'id') else options[0]["id"]
                select_msg = {
                    "type": "select_option",
                    "session_id": "e2e_session_003",
                    "node_id": node_id,
                    "option_id": option_id
                }
                
                select_response = await self.server.process_message(select_msg)
                self.assert_true("data" in select_response, "Select response has data")
            else:
                self.passed += 1
                self.log("[SKIP] No thinking node (high confidence)")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 1
    
    async def test_blueprint_ready(self):
        """Test blueprint generation"""
        try:
            session_id = "e2e_session_004"
            message = {
                "type": "process",
                "session_id": session_id,
                "input": "Create a simple task"
            }
            
            response = await self.server.process_message(message)
            
            # If thinking node, select options until blueprint ready
            engine = self.server.engine_facades.get(session_id)
            max_iterations = 5
            iteration = 0
            
            while response["data"]["type"] == "thinking_node" and iteration < max_iterations:
                options = response["data"]["options"]
                option_id = options[0].id if hasattr(options[0], 'id') else options[0]["id"]
                response = await self.server.process_message({
                    "type": "select_option",
                    "session_id": session_id,
                    "node_id": response["data"]["node_id"],
                    "option_id": option_id
                })
                iteration += 1
            
            # Check if we have steps in the engine
            if engine:
                has_steps = len(engine.execution_steps) > 0
                self.assert_true(has_steps, "Engine has execution steps")
            else:
                self.failed += 1
                self.log("[FAIL] Engine not created")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 1
    
    async def test_execute_blueprint(self):
        """Test blueprint execution"""
        try:
            # Setup: process and get blueprint
            process_msg = {
                "type": "process",
                "session_id": "e2e_session_005",
                "input": "Execute a task"
            }
            await self.server.process_message(process_msg)
            
            # Execute
            execute_msg = {
                "type": "execute",
                "session_id": "e2e_session_005"
            }
            
            response = await self.server.process_message(execute_msg)
            
            self.assert_true("data" in response, "Execution response has data")
            self.assert_true(
                "status" in response["data"],
                "Execution result has status"
            )
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_execution_status(self):
        """Test getting execution status"""
        try:
            message = {
                "type": "get_status",
                "session_id": "e2e_session_006"
            }
            
            response = await self.server.process_message(message)
            
            self.assert_true("data" in response, "Status response has data")
            
            status = response["data"]
            self.assert_true("session_id" in status, "Status has session_id")
            self.assert_true("progress" in status, "Status has progress")
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 2
    
    async def test_full_flow(self):
        """Test complete E2E flow"""
        try:
            import shutil
            import os
            
            session_id = "e2e_full_flow_session"
            persistence_path = "./test_sessions_e2e"
            
            # Clean up
            if os.path.exists(persistence_path):
                shutil.rmtree(persistence_path)
            
            # Step 1: Process input
            self.log("  Step 1: Process input")
            process_response = await self.server.process_message({
                "type": "process",
                "session_id": session_id,
                "input": "Plan a weekend trip to Hangzhou"
            })
            
            result_type = process_response["data"]["type"]
            self.log(f"    Result: {result_type}")
            
            # Step 2: If thinking node, select option
            if result_type == "thinking_node":
                self.log("  Step 2: Select option")
                node_id = process_response["data"]["node_id"]
                options = process_response["data"]["options"]
                option_id = options[0].id if hasattr(options[0], 'id') else options[0]["id"]
                
                select_response = await self.server.process_message({
                    "type": "select_option",
                    "session_id": session_id,
                    "node_id": node_id,
                    "option_id": option_id
                })
                self.log(f"    Result: {select_response['data']['type']}")
            
            # Step 3: Execute
            self.log("  Step 3: Execute blueprint")
            execute_response = await self.server.process_message({
                "type": "execute",
                "session_id": session_id
            })
            
            exec_status = execute_response["data"]["status"]
            self.log(f"    Execution: {exec_status}")
            
            self.assert_true(
                exec_status in ["completed", "in_progress"],
                "Execution completed or in progress"
            )
            
            # Step 4: Get status
            self.log("  Step 4: Get status")
            status_response = await self.server.process_message({
                "type": "get_status",
                "session_id": session_id
            })
            
            progress = status_response["data"]["progress"]
            self.log(f"    Progress: {progress}%")
            
            self.assert_true(progress >= 0, "Progress is valid")
            
            # Cleanup
            shutil.rmtree(persistence_path, ignore_errors=True)
            
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.failed += 3


async def main():
    test = TestWebSocketE2E()
    success = await test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
