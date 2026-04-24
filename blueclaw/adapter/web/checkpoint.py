# -*- coding: utf-8 -*-
"""
WebCheckpointManager - 浏览器页面状态检查点管理器

- 保存/恢复 DOM、Cookies、LocalStorage、SessionStorage、截图
- 与 core/checkpoint_v2.py（OperationRecord 检查点）互补
"""
import os
import json
import base64
import shutil
import time
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class WebCheckpoint(BaseModel):
    """浏览器页面状态检查点"""
    checkpoint_id: str
    blueprint_id: str
    step_id: str
    url: str = ""
    title: str = ""
    dom: str = ""
    cookies: List[Dict[str, Any]] = Field(default_factory=list)
    local_storage: Dict[str, str] = Field(default_factory=dict)
    session_storage: Dict[str, str] = Field(default_factory=dict)
    screenshot_b64: str = ""
    timestamp: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebCheckpoint":
        return cls.model_validate(data)


class WebCheckpointManager:
    """浏览器页面状态检查点管理器"""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "sessions", "web_checkpoints"
            )
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _dir(self, blueprint_id: str) -> str:
        return os.path.join(self.base_dir, blueprint_id)

    def _path(self, blueprint_id: str, checkpoint_id: str) -> str:
        return os.path.join(self._dir(blueprint_id), f"{checkpoint_id}.json")

    async def save(
        self,
        page,
        blueprint_id: str,
        step_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebCheckpoint:
        """保存当前页面状态为检查点"""
        checkpoint_id = f"wcp_{int(time.time() * 1000)}"

        # 捕获页面状态
        url = page.url
        title = await page.title()
        dom = await page.content()
        cookies = await page.context.cookies()

        # 通过 JS 捕获 storage（about:blank 或某些协议可能受限）
        try:
            local_storage = await page.evaluate("""() => {
                const data = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    data[key] = localStorage.getItem(key);
                }
                return data;
            }""")
        except Exception:
            local_storage = {}
        try:
            session_storage = await page.evaluate("""() => {
                const data = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    data[key] = sessionStorage.getItem(key);
                }
                return data;
            }""")
        except Exception:
            session_storage = {}

        # 截图
        screenshot_bytes = await page.screenshot(type="png")
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        checkpoint = WebCheckpoint(
            checkpoint_id=checkpoint_id,
            blueprint_id=blueprint_id,
            step_id=step_id,
            url=url,
            title=title,
            dom=dom,
            cookies=cookies,
            local_storage=local_storage or {},
            session_storage=session_storage or {},
            screenshot_b64=screenshot_b64,
            timestamp=time.time(),
            metadata=metadata or {},
        )

        d = self._dir(blueprint_id)
        os.makedirs(d, exist_ok=True)
        path = self._path(blueprint_id, checkpoint_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

        return checkpoint

    async def restore(self, page, blueprint_id: str, checkpoint_id: str) -> Optional[WebCheckpoint]:
        """从检查点恢复页面状态"""
        path = self._path(blueprint_id, checkpoint_id)
        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            checkpoint = WebCheckpoint.from_dict(json.load(f))

        # 恢复页面内容（优先使用 set_content 避免额外导航，但如果跨域则 goto）
        try:
            await page.set_content(checkpoint.dom, wait_until="networkidle", timeout=10000)
        except Exception:
            await page.goto(checkpoint.url, wait_until="networkidle", timeout=10000)

        # 恢复 cookies（需要先访问对应域，否则 add_cookies 可能失败）
        if checkpoint.cookies:
            try:
                await page.context.add_cookies(checkpoint.cookies)
            except Exception:
                pass

        # 恢复 localStorage
        if checkpoint.local_storage:
            await page.evaluate("""(data) => {
                for (const [k, v] of Object.entries(data)) {
                    localStorage.setItem(k, v);
                }
            }""", checkpoint.local_storage)

        # 恢复 sessionStorage
        if checkpoint.session_storage:
            await page.evaluate("""(data) => {
                for (const [k, v] of Object.entries(data)) {
                    sessionStorage.setItem(k, v);
                }
            }""", checkpoint.session_storage)

        return checkpoint

    def list_checkpoints(self, blueprint_id: str) -> List[Dict[str, Any]]:
        """列出某蓝图的所有页面状态检查点（按时间排序）"""
        d = self._dir(blueprint_id)
        if not os.path.exists(d):
            return []
        files = []
        for fname in os.listdir(d):
            if fname.endswith(".json"):
                path = os.path.join(d, fname)
                files.append({
                    "checkpoint_id": fname[:-5],
                    "path": path,
                    "mtime": os.path.getmtime(path),
                })
        files.sort(key=lambda x: x["mtime"])
        return files

    def cleanup(self, blueprint_id: str, keep_last_n: int = 10) -> int:
        """清理旧检查点，只保留最近 N 个"""
        checkpoints = self.list_checkpoints(blueprint_id)
        if len(checkpoints) <= keep_last_n:
            return 0
        removed = 0
        for cp in checkpoints[:-keep_last_n]:
            try:
                os.remove(cp["path"])
                removed += 1
            except Exception:
                pass
        return removed

    def delete_all(self, blueprint_id: str) -> None:
        """删除某蓝图的所有页面状态检查点"""
        d = self._dir(blueprint_id)
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
