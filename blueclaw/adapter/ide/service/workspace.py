# -*- coding: utf-8 -*-
"""
Workspace Service - 工作区管理

- 维护当前打开的项目路径
- 语言分布统计
- 工作区状态快照
"""
import os
from typing import Dict, Any, Optional

from blueclaw.adapter.ide.models import WorkspaceInfo, FileEntry
from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer


class WorkspaceService:
    """工作区服务"""

    def __init__(self, root_path: Optional[str] = None):
        self._root_path = os.path.abspath(root_path or ".")
        self._analyzer: Optional[CodebaseAnalyzer] = None

    @property
    def root_path(self) -> str:
        return self._root_path

    def set_root(self, path: str) -> None:
        """设置工作区根目录"""
        self._root_path = os.path.abspath(path)
        self._analyzer = None  # invalidate cache

    def get_info(self) -> WorkspaceInfo:
        """获取工作区信息"""
        name = os.path.basename(self._root_path)
        lang_dist: Dict[str, int] = {}
        if os.path.isdir(self._root_path):
            try:
                analyzer = CodebaseAnalyzer(self._root_path)
                analysis = analyzer.analyze(max_files=500)
                lang_dist = analysis.languages
            except Exception:
                pass
        return WorkspaceInfo(root_path=self._root_path, name=name, language_distribution=lang_dist)

    def resolve_path(self, rel_path: str) -> str:
        """将相对路径解析为绝对路径（限制在工作区内）"""
        abs_path = os.path.abspath(os.path.join(self._root_path, rel_path))
        # Security: ensure path stays within workspace
        if not abs_path.startswith(self._root_path):
            raise ValueError(f"Path escapes workspace: {rel_path}")
        return abs_path

    def relative_path(self, abs_path: str) -> str:
        """将绝对路径转为相对路径"""
        return os.path.relpath(abs_path, self._root_path)
