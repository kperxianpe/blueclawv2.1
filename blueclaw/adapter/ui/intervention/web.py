# -*- coding: utf-8 -*-
"""
WebInterventionUI - 轻量级 Web 页面实现（aiohttp）

支持：截图展示、Canvas 画圈标注、文字输入、按钮选择
"""
import asyncio
import base64
import webbrowser
from typing import Any, Optional
from aiohttp import web

from blueclaw.adapter.ui.intervention.base import InterventionUI, InterventionResult


class WebInterventionUI(InterventionUI):
    """Web 浏览器干预界面"""

    def __init__(self, port: int = 8080):
        self.port = port
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._event: Optional[asyncio.Event] = None
        self._result: Optional[InterventionResult] = None

    async def _start_server(self) -> None:
        if self._runner is not None:
            return
        self._app = web.Application()
        self._app.router.add_get("/intervention", self._handle_page)
        self._app.router.add_post("/submit", self._handle_submit)
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "127.0.0.1", self.port)
        await self._site.start()

    async def shutdown(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            self._site = None
            self._app = None

    async def show(self, step: Any, screenshot: bytes, error_info: str = None) -> InterventionResult:
        await self._start_server()
        self._event = asyncio.Event()
        self._result = None

        self._page_data = {
            "step_name": getattr(step, "name", "unknown"),
            "screenshot_b64": base64.b64encode(screenshot).decode("utf-8"),
            "error_info": error_info or "",
            "annotations": getattr(step, "action", {}).get("params", {}).get("user_annotation", None) if hasattr(step, "action") else None,
        }

        # 尝试打开浏览器
        try:
            webbrowser.open(f"http://127.0.0.1:{self.port}/intervention")
        except Exception:
            pass

        # 等待用户提交（带 300 秒超时）
        try:
            await asyncio.wait_for(self._event.wait(), timeout=300)
        except asyncio.TimeoutError:
            pass
        finally:
            await self.shutdown()

        return self._result or InterventionResult(type="button", choice="retry")

    async def _handle_page(self, request: web.Request) -> web.Response:
        data = getattr(self, "_page_data", {})
        html = self._generate_page(
            data.get("screenshot_b64", ""),
            data.get("step_name", "unknown"),
            data.get("error_info", ""),
            data.get("annotations"),
        )
        return web.Response(text=html, content_type="text/html")

    async def _handle_submit(self, request: web.Request) -> web.Response:
        payload = await request.json()
        self._result = InterventionResult(
            type="button",
            choice=payload.get("choice", "retry"),
            annotation=payload.get("annotation"),
            text=payload.get("text") or None,
            param_changes=payload.get("param_changes", {}),
        )
        self._event.set()
        return web.json_response({"status": "ok"})

    def _generate_page(self, screenshot_b64: str, step_name: str, error: str, annotations=None) -> str:
        anno_js = ""
        if annotations:
            anno_js = f"""
            const preAnno = {annotations};
            if (preAnno && preAnno.type === 'circle') {{
                ctx.beginPath();
                ctx.arc(preAnno.x * canvas.width, preAnno.y * canvas.height, canvas.width * preAnno.radius, 0, Math.PI * 2);
                ctx.strokeStyle = 'red';
                ctx.lineWidth = 3;
                ctx.stroke();
            }}
            """
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>干预 - {step_name}</title>
<style>
  body {{ font-family: sans-serif; padding: 20px; background: #f5f5f5; }}
  #canvas {{ border: 1px solid #ccc; background: #fff; cursor: crosshair; max-width: 100%; }}
  .controls {{ margin-top: 20px; }}
  button {{ margin-right: 10px; padding: 10px 20px; font-size: 14px; cursor: pointer; }}
  textarea {{ width: 100%; max-width: 600px; }}
  .error {{ color: #c00; margin: 10px 0; }}
</style>
</head>
<body>
  <h2>步骤干预: {step_name}</h2>
  {f'<div class="error">错误: {error}</div>' if error else ''}
  <canvas id="canvas" width="800" height="600"></canvas>
  <p>提示: 在截图上点击画圈标注问题位置</p>
  <div class="controls">
    <textarea id="description" rows="3" cols="60" placeholder="描述问题或补充说明..."></textarea><br><br>
    <button onclick="submit('retry')">重试</button>
    <button onclick="submit('skip')">跳过</button>
    <button onclick="submit('replan')">重新规划</button>
    <button onclick="submit('abort')">中止</button>
  </div>
  <script>
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.src = 'data:image/webp;base64,{screenshot_b64}';
    img.onload = function() {{
      canvas.width = img.naturalWidth > 800 ? 800 : img.naturalWidth;
      canvas.height = img.naturalHeight > 600 ? 600 : img.naturalHeight;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      {anno_js}
    }};
    let annotations = [];
    canvas.addEventListener('mousedown', function(e) {{
      const rect = canvas.getBoundingClientRect();
      const x = (e.clientX - rect.left) / canvas.width;
      const y = (e.clientY - rect.top) / canvas.height;
      annotations.push({{type: 'circle', x: x, y: y, radius: 0.03}});
      ctx.beginPath();
      ctx.arc(e.clientX - rect.left, e.clientY - rect.top, canvas.width * 0.03, 0, Math.PI * 2);
      ctx.strokeStyle = 'red';
      ctx.lineWidth = 2;
      ctx.stroke();
    }});
    function submit(choice) {{
      fetch('/submit', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          choice: choice,
          annotation: annotations[0] || null,
          text: document.getElementById('description').value,
          param_changes: {{}}
        }})
      }}).then(() => {{
        document.body.innerHTML = '<h2>已提交，请返回控制台继续</h2>';
      }});
    }}
  </script>
</body>
</html>"""
