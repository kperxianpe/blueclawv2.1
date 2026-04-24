# -*- coding: utf-8 -*-
"""
IDE API Router - 路由聚合

Usage:
    from fastapi import FastAPI
    from blueclaw.adapter.ide.api.router import register_ide_routes

    app = FastAPI()
    register_ide_routes(app, workspace_path="/path/to/project")
"""
from fastapi import FastAPI

from blueclaw.adapter.ide.api import filesystem, runner, test_runner, kimicode, websocket
from blueclaw.adapter.ide.service.workspace import WorkspaceService


def register_ide_routes(app: FastAPI, workspace_path: str = "."):
    """注册所有 IDE 路由到 FastAPI app"""
    ws = WorkspaceService(workspace_path)

    filesystem.set_workspace(ws)
    runner.set_workspace(ws)
    test_runner.set_workspace(ws)
    kimicode.set_workspace(ws)

    app.include_router(filesystem.router, prefix="/api/ide")
    app.include_router(runner.router, prefix="/api/ide")
    app.include_router(test_runner.router, prefix="/api/ide")
    app.include_router(kimicode.router, prefix="/api/ide")

    # WebSocket endpoint
    from fastapi import WebSocket

    @app.websocket("/ws/ide")
    async def ide_websocket_endpoint(websocket: WebSocket):
        await websocket.handle_ide_websocket(websocket)

    return ws
