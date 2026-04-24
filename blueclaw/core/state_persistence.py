# -*- coding: utf-8 -*-
"""
state_persistence.py - 状态持久化

职责: 保存和恢复会话状态
"""

import json
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import asdict


class StatePersistence:
    """状态持久化"""
    
    def __init__(self, storage_dir: str = "./memory/sessions"):
        """
        初始化持久化
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 会话元数据文件
        self.metadata_file = self.storage_dir / "sessions.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """加载元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {"sessions": []}
    
    def _save_metadata(self):
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
    
    def save_session(
        self,
        session_id: str,
        thinking_chain,
        execution_steps: List[Any],
        additional_data: Dict[str, Any] = None
    ) -> Path:
        """
        保存会话状态
        
        Args:
            session_id: 会话ID
            thinking_chain: 思考链
            execution_steps: 执行步骤
            additional_data: 附加数据
            
        Returns:
            Path: 保存的文件路径
        """
        additional_data = additional_data or {}
        
        # 准备数据
        data = {
            "session_id": session_id,
            "saved_at": datetime.now().isoformat(),
            "thinking_chain": self._serialize_chain(thinking_chain),
            "execution_steps": [self._serialize_step(s) for s in execution_steps],
            "additional_data": additional_data
        }
        
        # 保存为JSON
        file_path = self.storage_dir / f"{session_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        # 更新元数据
        self._update_metadata(session_id, file_path)
        
        return file_path
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict]: 会话数据，不存在返回None
        """
        file_path = self.storage_dir / f"{session_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功删除
        """
        file_path = self.storage_dir / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            
            # 更新元数据
            self.metadata["sessions"] = [
                s for s in self.metadata["sessions"]
                if s["session_id"] != session_id
            ]
            self._save_metadata()
            
            return True
        return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        列出所有会话
        
        Returns:
            List[Dict]: 会话列表
        """
        return self.metadata.get("sessions", [])
    
    def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否存在
        """
        file_path = self.storage_dir / f"{session_id}.json"
        return file_path.exists()
    
    def _update_metadata(self, session_id: str, file_path: Path):
        """更新元数据"""
        # 查找或创建会话记录
        existing = None
        for s in self.metadata["sessions"]:
            if s["session_id"] == session_id:
                existing = s
                break
        
        if existing:
            existing["updated_at"] = datetime.now().isoformat()
            existing["file_path"] = str(file_path)
        else:
            self.metadata["sessions"].append({
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "file_path": str(file_path)
            })
        
        self._save_metadata()
    
    def _serialize_chain(self, thinking_chain) -> Dict[str, Any]:
        """序列化思考链"""
        if thinking_chain is None:
            return None
        
        # 如果思考链有 to_dict 方法，使用它
        if hasattr(thinking_chain, 'to_dict'):
            return thinking_chain.to_dict()
        
        # 否则尝试简单序列化
        return {
            "session_id": getattr(thinking_chain, 'session_id', None),
            "root_node_id": getattr(thinking_chain, 'root_node_id', None),
            "current_node_id": getattr(thinking_chain, 'current_node_id', None),
        }
    
    def _serialize_step(self, step) -> Dict[str, Any]:
        """序列化步骤"""
        if step is None:
            return None
        
        # 如果是 dataclass，使用 asdict
        if hasattr(step, '__dataclass_fields__'):
            data = asdict(step)
            # 处理枚举类型
            if hasattr(step, 'status'):
                data['status'] = step.status.value if hasattr(step.status, 'value') else str(step.status)
            return data
        
        # 否则尝试获取 __dict__
        if hasattr(step, '__dict__'):
            return step.__dict__
        
        return {"error": "Cannot serialize step"}
    
    def save_checkpoint(
        self,
        session_id: str,
        checkpoint_name: str,
        data: Dict[str, Any]
    ) -> Path:
        """
        保存检查点
        
        Args:
            session_id: 会话ID
            checkpoint_name: 检查点名称
            data: 数据
            
        Returns:
            Path: 文件路径
        """
        checkpoint_dir = self.storage_dir / "checkpoints" / session_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = checkpoint_dir / f"{checkpoint_name}.json"
        
        checkpoint_data = {
            "session_id": session_id,
            "checkpoint_name": checkpoint_name,
            "saved_at": datetime.now().isoformat(),
            "data": data
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False, default=str)
        
        return file_path
    
    def load_checkpoint(
        self,
        session_id: str,
        checkpoint_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        加载检查点
        
        Args:
            session_id: 会话ID
            checkpoint_name: 检查点名称
            
        Returns:
            Optional[Dict]: 数据
        """
        file_path = self.storage_dir / "checkpoints" / session_id / f"{checkpoint_name}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def export_session(
        self,
        session_id: str,
        export_path: str
    ) -> Path:
        """
        导出会话（用于分享或备份）
        
        Args:
            session_id: 会话ID
            export_path: 导出路径
            
        Returns:
            Path: 导出文件路径
        """
        session_data = self.load_session(session_id)
        if not session_data:
            raise ValueError(f"Session not found: {session_id}")
        
        export_file = Path(export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        return export_file
    
    def import_session(self, import_path: str) -> str:
        """
        导入会话
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            str: 导入后的会话ID
        """
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 生成新的会话ID避免冲突
        original_id = data.get("session_id", "unknown")
        new_id = f"{original_id}_imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        data["session_id"] = new_id
        data["imported_at"] = datetime.now().isoformat()
        
        # 保存
        file_path = self.storage_dir / f"{new_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self._update_metadata(new_id, file_path)
        
        return new_id
