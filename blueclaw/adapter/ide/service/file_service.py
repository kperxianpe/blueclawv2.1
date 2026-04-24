# -*- coding: utf-8 -*-
"""
File Service - 文件系统操作

- 文件树浏览
- 文件 CRUD
- 语言检测
"""
import os
import mimetypes
from typing import List, Optional
from pathlib import Path

from blueclaw.adapter.ide.models import (
    FileEntry, FileTreeResponse, FileContent,
    FileOperationResult, FileWriteRequest, FileCreateRequest, FileRenameRequest,
)
from blueclaw.adapter.ide.service.workspace import WorkspaceService


# 常见语言映射
EXT_TO_LANGUAGE = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp",
    ".h": "c", ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby",
    ".php": "php", ".swift": "swift", ".kt": "kotlin",
    ".scala": "scala", ".r": "r", ".m": "matlab",
    ".html": "html", ".css": "css", ".scss": "scss",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".xml": "xml", ".md": "markdown", ".sql": "sql",
    ".sh": "shell", ".bash": "shell", ".ps1": "powershell",
    ".dockerfile": "dockerfile", ".tf": "terraform",
}


def detect_language(file_path: str) -> str:
    """根据扩展名检测编程语言"""
    ext = os.path.splitext(file_path)[1].lower()
    basename = os.path.basename(file_path).lower()
    if basename == "dockerfile":
        return "dockerfile"
    if basename == "makefile":
        return "makefile"
    return EXT_TO_LANGUAGE.get(ext, "")


class FileService:
    """文件服务"""

    def __init__(self, workspace: WorkspaceService):
        self.workspace = workspace

    def list_tree(self, rel_path: str = "", depth: int = 1) -> FileTreeResponse:
        """列出文件树"""
        abs_path = self.workspace.resolve_path(rel_path)
        entries: List[FileEntry] = []

        if os.path.isdir(abs_path):
            try:
                for name in sorted(os.listdir(abs_path)):
                    if name.startswith("."):
                        continue
                    child_abs = os.path.join(abs_path, name)
                    child_rel = os.path.join(rel_path, name).replace("\\", "/")
                    if os.path.isdir(child_abs):
                        entries.append(FileEntry(name=name, path=child_rel, type="directory"))
                    else:
                        stat = os.stat(child_abs)
                        entries.append(FileEntry(
                            name=name, path=child_rel, type="file",
                            size=stat.st_size, modified_time=stat.st_mtime,
                            language=detect_language(name),
                        ))
            except PermissionError:
                pass

        return FileTreeResponse(path=rel_path, entries=entries)

    def read_file(self, rel_path: str) -> FileContent:
        """读取文件内容"""
        abs_path = self.workspace.resolve_path(rel_path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"File not found: {rel_path}")

        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        return FileContent(
            path=rel_path,
            content=content,
            language=detect_language(abs_path),
            line_count=len(lines),
        )

    def write_file(self, req: FileWriteRequest) -> FileOperationResult:
        """写入文件"""
        abs_path = self.workspace.resolve_path(req.path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding=req.encoding) as f:
            f.write(req.content)
        return FileOperationResult(success=True, path=req.path, message="File saved")

    def create(self, req: FileCreateRequest) -> FileOperationResult:
        """创建文件或目录"""
        abs_path = self.workspace.resolve_path(req.path)
        if req.type == "directory":
            os.makedirs(abs_path, exist_ok=True)
            return FileOperationResult(success=True, path=req.path, message="Directory created")
        else:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            Path(abs_path).touch()
            return FileOperationResult(success=True, path=req.path, message="File created")

    def delete(self, rel_path: str) -> FileOperationResult:
        """删除文件或目录"""
        abs_path = self.workspace.resolve_path(rel_path)
        if os.path.isdir(abs_path):
            import shutil
            shutil.rmtree(abs_path)
            return FileOperationResult(success=True, path=rel_path, message="Directory deleted")
        else:
            os.remove(abs_path)
            return FileOperationResult(success=True, path=rel_path, message="File deleted")

    def rename(self, req: FileRenameRequest) -> FileOperationResult:
        """重命名文件或目录"""
        old_abs = self.workspace.resolve_path(req.old_path)
        new_abs = self.workspace.resolve_path(req.new_path)
        os.makedirs(os.path.dirname(new_abs), exist_ok=True)
        os.rename(old_abs, new_abs)
        return FileOperationResult(success=True, path=req.new_path, message="Renamed successfully")
