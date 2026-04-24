#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理器 - 管理所有任务的生命周期
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Optional
from models.task import Task, TaskStatus
from models.messages import Message


class TaskManager:
    def __init__(self):
        # 内存中的任务存储
        self.tasks: Dict[str, Task] = {}
        # WebSocket 服务器引用（用于推送消息）
        self.server = None
    
    def set_server(self, server):
        """设置 WebSocket 服务器引用"""
        self.server = server
    
    async def create_task(self, user_input: str) -> Task:
        """创建新任务"""
        from core.checkpoint import checkpoint_manager
        
        task = Task.create(user_input)
        self.tasks[task.id] = task
        
        # 保存初始检查点
        await checkpoint_manager.save_checkpoint(task)
        
        print(f"Task created: {task.id}")
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """获取所有任务"""
        return self.tasks.copy()
    
    async def update_task_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        from core.checkpoint import checkpoint_manager
        
        task = self.get_task(task_id)
        if task:
            task.update_status(status)
            
            # 保存检查点
            await checkpoint_manager.save_checkpoint(task)
            
            # 推送状态更新
            if self.server:
                await self.server.broadcast_to_task(
                    task_id,
                    Message.create(
                        "task.status_updated",
                        {"status": status.value},
                        task_id=task_id
                    ).to_dict()
                )
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.update_status(TaskStatus.CANCELLED)
        
        # 推送取消通知
        if self.server:
            await self.server.broadcast_to_task(
                task_id,
                Message.create(
                    "task.cancelled",
                    {"reason": "user_request"},
                    task_id=task_id
                ).to_dict()
            )
        
        return True
    
    async def add_thinking_node(self, task_id: str, node: dict):
        """添加思考节点到任务"""
        from core.checkpoint import checkpoint_manager
        
        task = self.get_task(task_id)
        if task:
            task.thinking_path.append(node)
            task.update_status(TaskStatus.THINKING)
            await checkpoint_manager.save_checkpoint(task)
    
    async def set_execution_blueprint(self, task_id: str, blueprint: dict):
        """设置执行蓝图"""
        from core.checkpoint import checkpoint_manager
        
        task = self.get_task(task_id)
        if task:
            task.execution_blueprint = blueprint
            task.update_status(TaskStatus.THINKING_COMPLETED)
            await checkpoint_manager.save_checkpoint(task)


# 全局任务管理器实例
task_manager = TaskManager()
