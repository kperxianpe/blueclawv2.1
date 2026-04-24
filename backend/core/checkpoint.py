#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checkpoint 管理器 - 任务状态持久化
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, Dict, List
from datetime import datetime
from models.task import Task, TaskStatus


class CheckpointManager:
    def __init__(self, storage_dir: str = "./checkpoints"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_checkpoint_path(self, task_id: str) -> str:
        """获取检查点文件路径"""
        return os.path.join(self.storage_dir, f"{task_id}.json")
    
    async def save_checkpoint(self, task: Task) -> bool:
        """
        保存任务检查点
        将任务状态保存到 JSON 文件
        """
        try:
            checkpoint_data = {
                "task": task.to_dict(),
                "saved_at": datetime.now().isoformat(),
                "version": 1
            }
            
            filepath = self._get_checkpoint_path(task.id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            print(f"Checkpoint saved: {task.id}")
            return True
        except Exception as e:
            print(f"Failed to save checkpoint: {e}")
            return False
    
    async def load_checkpoint(self, task_id: str) -> Optional[Task]:
        """
        从检查点恢复任务
        """
        filepath = self._get_checkpoint_path(task_id)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            task_dict = data.get("task", {})
            
            # 重建 Task 对象
            task = Task(
                id=task_dict["id"],
                user_input=task_dict["user_input"],
                status=TaskStatus(task_dict["status"]),
                created_at=task_dict["created_at"],
                updated_at=task_dict["updated_at"],
                thinking_path=task_dict.get("thinking_path", []),
                execution_blueprint=task_dict.get("execution_blueprint"),
                current_step_id=task_dict.get("current_step_id"),
                context=task_dict.get("context", {})
            )
            
            print(f"Checkpoint loaded: {task_id}")
            return task
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
            return None
    
    async def delete_checkpoint(self, task_id: str) -> bool:
        """删除检查点"""
        filepath = self._get_checkpoint_path(task_id)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Checkpoint deleted: {task_id}")
            return True
        return False
    
    async def list_checkpoints(self) -> List[Dict]:
        """列出所有检查点"""
        checkpoints = []
        
        if not os.path.exists(self.storage_dir):
            return checkpoints
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    checkpoints.append({
                        "task_id": data["task"]["id"],
                        "saved_at": data["saved_at"],
                        "status": data["task"]["status"]
                    })
                except:
                    pass
        
        return checkpoints
    
    async def restore_all_tasks(self, task_manager) -> int:
        """
        服务启动时恢复所有任务
        返回恢复的任务数量
        """
        checkpoints = await self.list_checkpoints()
        restored = 0
        
        for cp in checkpoints:
            task = await self.load_checkpoint(cp["task_id"])
            if task:
                task_manager.tasks[task.id] = task
                restored += 1
        
        print(f"Restored {restored} tasks from checkpoints")
        return restored


# 全局检查点管理器实例
checkpoint_manager = CheckpointManager()
