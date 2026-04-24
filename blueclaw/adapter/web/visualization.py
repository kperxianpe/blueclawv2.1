# -*- coding: utf-8 -*-
"""
CanvasMindVisualizer - 在目标页面注入可视化层

- 操作标记（红圈脉冲）
- 检查点旗帜
- 干扰元素高亮
- 进度条
- 清除覆盖层
"""
from typing import List, Optional

from blueclaw.adapter.web.models import WebElement


_SHARED_CSS = """
.blueclaw-overlay {
  position: fixed;
  z-index: 999999;
  pointer-events: none;
  font-family: sans-serif;
}
@keyframes blueclaw-pulse {
  0% { transform: translate(-50%, -50%) scale(0.8); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
}
.blueclaw-op-mark {
  position: absolute;
  width: 40px;
  height: 40px;
  border: 3px solid #ff4444;
  border-radius: 50%;
  animation: blueclaw-pulse 1.2s ease-out infinite;
  pointer-events: none;
}
.blueclaw-cp-flag {
  position: absolute;
  width: 0;
  height: 0;
  border-left: 10px solid #2196f3;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  pointer-events: none;
}
.blueclaw-cp-flag::after {
  content: 'CP';
  position: absolute;
  left: -28px;
  top: -10px;
  background: #2196f3;
  color: white;
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 3px;
}
.blueclaw-distraction {
  position: absolute;
  background: rgba(255, 235, 59, 0.4);
  border: 2px dashed #f9a825;
  pointer-events: none;
}
.blueclaw-progress-bar {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 28px;
  background: rgba(0,0,0,0.75);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  font-size: 12px;
  z-index: 999999;
  pointer-events: none;
}
.blueclaw-progress-fill {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  background: linear-gradient(90deg, #4caf50, #8bc34a);
  opacity: 0.4;
  transition: width 0.3s ease;
  z-index: -1;
}
"""


class CanvasMindVisualizer:
    """页面可视化注入器"""

    async def inject_overlay(self, page) -> None:
        """注入共享 CSS"""
        await page.evaluate(f"""(css) => {{
            if (document.getElementById('blueclaw-style')) return;
            const style = document.createElement('style');
            style.id = 'blueclaw-style';
            style.textContent = css;
            document.head.appendChild(style);
        }}""", _SHARED_CSS)

    async def mark_operation(
        self,
        page,
        element: Optional[WebElement] = None,
        action_type: str = "click",
    ) -> None:
        """在元素位置绘制红圈脉冲"""
        if element is None:
            return
        coords = element.normalized_coords
        await page.evaluate("""(data) => {
            const mark = document.createElement('div');
            mark.className = 'blueclaw-op-mark blueclaw-overlay';
            mark.style.left = (data.x * 100) + '%';
            mark.style.top = (data.y * 100) + '%';
            mark.dataset.blueclaw = '1';
            document.body.appendChild(mark);
            setTimeout(() => mark.remove(), 3000);
        }""", {"x": coords.get("x", 0), "y": coords.get("y", 0)})

    async def mark_checkpoint(
        self,
        page,
        element: Optional[WebElement] = None,
    ) -> None:
        """在元素位置或页面角落绘制检查点旗帜"""
        x = element.normalized_coords.get("x", 0.02) if element else 0.02
        y = element.normalized_coords.get("y", 0.02) if element else 0.02
        await page.evaluate("""(data) => {
            const flag = document.createElement('div');
            flag.className = 'blueclaw-cp-flag blueclaw-overlay';
            flag.style.left = (data.x * 100) + '%';
            flag.style.top = (data.y * 100) + '%';
            flag.dataset.blueclaw = '1';
            document.body.appendChild(flag);
        }""", {"x": x, "y": y})

    async def highlight_distractions(
        self,
        page,
        distractions: List[WebElement],
    ) -> None:
        """给干扰元素添加黄色半透明遮罩"""
        rects = []
        for d in distractions:
            nc = d.normalized_coords
            rects.append({
                "x": nc.get("x", 0),
                "y": nc.get("y", 0),
                "width": nc.get("width", 0),
                "height": nc.get("height", 0),
            })
        if not rects:
            return
        await page.evaluate("""(rects) => {
            rects.forEach(r => {
                const div = document.createElement('div');
                div.className = 'blueclaw-distraction blueclaw-overlay';
                div.style.left = (r.x * 100) + '%';
                div.style.top = (r.y * 100) + '%';
                div.style.width = (r.width * 100) + '%';
                div.style.height = (r.height * 100) + '%';
                div.dataset.blueclaw = '1';
                document.body.appendChild(div);
            });
        }""", rects)

    async def show_progress(
        self,
        page,
        current_step: int,
        total_steps: int,
        duration_ms: float = 0.0,
    ) -> None:
        """在页面顶部显示浮动进度条"""
        pct = (current_step / total_steps * 100) if total_steps > 0 else 0
        text = f"Step {current_step}/{total_steps} | {duration_ms/1000:.1f}s"
        await page.evaluate("""(data) => {
            let bar = document.getElementById('blueclaw-progress');
            if (!bar) {
                bar = document.createElement('div');
                bar.id = 'blueclaw-progress';
                bar.className = 'blueclaw-progress-bar blueclaw-overlay';
                bar.innerHTML = '<div class=\"blueclaw-progress-fill\"></div><span id=\"blueclaw-progress-text\"></span>';
                document.body.appendChild(bar);
            }
            bar.querySelector('.blueclaw-progress-fill').style.width = data.pct + '%';
            bar.querySelector('#blueclaw-progress-text').textContent = data.text;
        }""", {"pct": pct, "text": text})

    async def clear_overlays(self, page) -> None:
        """清除所有注入的可视化元素"""
        await page.evaluate("""() => {
            const style = document.getElementById('blueclaw-style');
            if (style) style.remove();
            const bar = document.getElementById('blueclaw-progress');
            if (bar) bar.remove();
            document.querySelectorAll('[data-blueclaw]').forEach(el => el.remove());
        }""")
