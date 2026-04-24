# -*- coding: utf-8 -*-
"""
KimiCode API - KimiCode 路由

POST /api/ide/kimicode/chat       (SSE)
POST /api/ide/kimicode/generate
POST /api/ide/kimicode/inline
POST /api/ide/kimicode/diff
GET  /api/ide/kimicode/diff/preview
POST /api/ide/kimicode/diff/apply
POST /api/ide/kimicode/diff/discard
GET  /api/ide/kimicode/sessions
"""
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from blueclaw.adapter.ide.models import (
    KimiCodeChatRequest, KimiCodeGenerateRequest, KimiCodeGenerateResponse,
    KimiCodeInlineRequest, KimiCodeInlineResponse,
    KimiCodeDiffRequest, KimiCodeDiffResponse, KimiCodeDiffPreviewResponse,
    KimiCodeDiffApplyRequest, KimiCodeDiffApplyResponse,
    KimiCodeSessionInfo,
)
from blueclaw.adapter.ide.service.kimicode_service import KimiCodeService
from blueclaw.adapter.ide.service.workspace import WorkspaceService


router = APIRouter(prefix="/kimicode", tags=["IDE KimiCode"])

_workspace: WorkspaceService = WorkspaceService()
_kimicode_service: KimiCodeService = KimiCodeService(
    api_key=os.getenv("KIMI_API_KEY"),
    workspace_path=_workspace.root_path,
)


def set_workspace(ws: WorkspaceService):
    global _workspace, _kimicode_service
    _workspace = ws
    _kimicode_service = KimiCodeService(
        api_key=os.getenv("KIMI_API_KEY"),
        workspace_path=ws.root_path,
    )


@router.post("/chat")
async def chat(req: KimiCodeChatRequest):
    """KimiCode 聊天（SSE 流式）"""
    async def event_generator():
        async for chunk in _kimicode_service.chat(req):
            yield chunk
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/generate", response_model=KimiCodeGenerateResponse)
async def generate(req: KimiCodeGenerateRequest):
    """生成代码"""
    return await _kimicode_service.generate(req)


@router.post("/inline", response_model=KimiCodeInlineResponse)
async def inline_complete(req: KimiCodeInlineRequest):
    """内联补全"""
    return await _kimicode_service.inline_complete(req)


@router.post("/diff", response_model=KimiCodeDiffResponse)
async def generate_diff(req: KimiCodeDiffRequest):
    """生成 Diff"""
    return await _kimicode_service.generate_diff(req)


@router.get("/diff/preview", response_model=KimiCodeDiffPreviewResponse)
async def preview_diff(diff_id: str = Query(...)):
    """预览 Diff"""
    return _kimicode_service.preview_diff(diff_id)


@router.post("/diff/apply", response_model=KimiCodeDiffApplyResponse)
async def apply_diff(req: KimiCodeDiffApplyRequest):
    """应用 Diff"""
    return _kimicode_service.apply_diff(req)


@router.post("/diff/discard")
async def discard_diff(diff_id: str):
    """丢弃 Diff"""
    success = _kimicode_service.discard_diff(diff_id)
    if not success:
        raise HTTPException(status_code=404, detail="Diff not found")
    return {"success": True}


@router.get("/sessions", response_model=list[KimiCodeSessionInfo])
async def list_sessions():
    """列出所有 KimiCode 会话"""
    return _kimicode_service.list_sessions()
