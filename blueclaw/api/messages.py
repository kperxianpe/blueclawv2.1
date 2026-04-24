#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Message Helpers - 简化消息创建
"""

from typing import Optional, List, Dict, Any
import uuid
import time


class Message:
    """简化消息创建类"""

    @staticmethod
    def create(msg_type: str, payload: dict, task_id: str = None) -> dict:
        """通用消息创建器（适配 adapter handlers 等通用场景）"""
        msg = {
            "type": msg_type,
            "payload": payload or {},
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
        if task_id:
            msg["payload"]["task_id"] = task_id
        return msg

    @staticmethod
    def task_started(task_id: str, user_input: str) -> dict:
        return {
            "type": "task.started",
            "payload": {
                "task_id": task_id,
                "user_input": user_input
            },
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
    
    @staticmethod
    def thinking_option_selected(
        task_id: str,
        option_id: str,
        has_more: bool = False,
        final_path: List[dict] = None,
        current_node_id: str = None
    ) -> dict:
        return {
            "type": "thinking.option_selected",
            "payload": {
                "task_id": task_id,
                "option_id": option_id,
                "current_node_id": current_node_id,
                "has_more_options": has_more,
                "final_path": final_path or []
            },
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
    
    @staticmethod
    def thinking_custom_input_received(
        task_id: str,
        has_more: bool = False,
        final_path: List[dict] = None,
        current_node_id: str = None,
        custom_input: str = None
    ) -> dict:
        payload = {
            "task_id": task_id,
            "has_more_options": has_more,
            "final_path": final_path or []
        }
        if current_node_id:
            payload["current_node_id"] = current_node_id
        if custom_input:
            payload["custom_input"] = custom_input
        return {
            "type": "thinking.custom_input_received",
            "payload": payload,
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
    
    @staticmethod
    def thinking_execution_confirmed(
        task_id: str,
        blueprint_id: str,
        blueprint_data: dict
    ) -> dict:
        return {
            "type": "thinking.execution_confirmed",
            "payload": {
                "task_id": task_id,
                "blueprint_id": blueprint_id,
                "blueprint": blueprint_data
            },
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
    
    @staticmethod
    def execution_started(task_id: str, blueprint_id: str) -> dict:
        return {
            "type": "execution.started",
            "payload": {
                "task_id": task_id,
                "blueprint_id": blueprint_id
            },
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
    
    @staticmethod
    def execution_paused(task_id: str, blueprint_id: str) -> dict:
        return {
            "type": "execution.paused",
            "payload": {
                "task_id": task_id,
                "blueprint_id": blueprint_id
            },
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
    
    @staticmethod
    def execution_resumed(task_id: str, blueprint_id: str) -> dict:
        return {
            "type": "execution.resumed",
            "payload": {
                "task_id": task_id,
                "blueprint_id": blueprint_id
            },
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
    
    @staticmethod
    def execution_intervened(
        task_id: str,
        blueprint_id: str,
        step_id: str,
        action: str,
        result: dict
    ) -> dict:
        return {
            "type": "execution.intervened",
            "payload": {
                "task_id": task_id,
                "blueprint_id": blueprint_id,
                "step_id": step_id,
                "action": action,
                "result": result
            },
            "timestamp": int(time.time() * 1000),
            "message_id": str(uuid.uuid4())[:8]
        }
