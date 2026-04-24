# -*- coding: utf-8 -*-
"""
Filesystem API - 文件系统路由

GET  /api/ide/fs/tree
GET  /api/ide/fs/read
POST /api/ide/fs/write
POST /api/ide/fs/create
DELETE /api/ide/fs/delete
POST /api/ide/fs/rename
"""
from fastapi import APIRouter, Query, HTTPException

from blueclaw.adapter.ide.models import (
    FileTreeResponse, FileContent, FileWriteRequest,
    FileCreateRequest, FileRenameRequest, FileOperationResult,
)
from blueclaw.adapter.ide.service.file_service import FileService
from blueclaw.adapter.ide.service.workspace import WorkspaceService


router = APIRouter(prefix="/fs", tags=["IDE Filesystem"])

# Global service instances (will be injected by main app in production)
_workspace: WorkspaceService = WorkspaceService()
_file_service: FileService = FileService(_workspace)


def set_workspace(ws: WorkspaceService):
    global _workspace, _file_service
    _workspace = ws
    _file_service = FileService(ws)


@router.get("/tree", response_model=FileTreeResponse)
async def get_tree(path: str = "", depth: int = Query(1, ge=1, le=10)):
    """获取文件树"""
    return _file_service.list_tree(path)


@router.get("/read", response_model=FileContent)
async def read_file(path: str):
    """读取文件内容"""
    try:
        return _file_service.read_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write", response_model=FileOperationResult)
async def write_file(req: FileWriteRequest):
    """写入文件"""
    try:
        return _file_service.write_file(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=FileOperationResult)
async def create_item(req: FileCreateRequest):
    """创建文件或目录"""
    try:
        return _file_service.create(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_item(path: str):
    """删除文件或目录"""
    try:
        return _file_service.delete(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rename", response_model=FileOperationResult)
async def rename_item(req: FileRenameRequest):
    """重命名文件或目录"""
    try:
        return _file_service.rename(req)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {req.old_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
