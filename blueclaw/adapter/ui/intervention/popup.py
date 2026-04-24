# -*- coding: utf-8 -*-
"""
PopupInterventionUI - Tkinter 弹窗备选
"""
import asyncio
from typing import Any
from blueclaw.adapter.ui.intervention.base import InterventionUI, InterventionResult


class PopupInterventionUI(InterventionUI):
    """Tkinter 弹窗干预界面"""

    def __init__(self):
        self._result: InterventionResult = InterventionResult(type="button", choice="retry")

    async def show(self, step: Any, screenshot: bytes, error_info: str = None) -> InterventionResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._show_sync, step, screenshot, error_info)

    def _show_sync(self, step: Any, screenshot: bytes, error_info: str = None) -> InterventionResult:
        import tkinter as tk
        from tkinter import messagebox
        try:
            from PIL import Image, ImageTk
            import io
            root = tk.Tk()
            root.title(f"干预 - {getattr(step, 'name', 'unknown')}")

            # 截图展示
            img = Image.open(io.BytesIO(screenshot))
            img.thumbnail((600, 400))
            photo = ImageTk.PhotoImage(img)
            label = tk.Label(root, image=photo)
            label.pack()

            # 错误信息
            if error_info:
                tk.Label(root, text=f"错误: {error_info}", fg="red").pack()

            result_container = {}

            def make_choice(choice: str):
                result_container["choice"] = choice
                result_container["text"] = text_var.get()
                root.destroy()

            text_var = tk.StringVar()
            tk.Entry(root, textvariable=text_var, width=50).pack()

            btn_frame = tk.Frame(root)
            btn_frame.pack()
            for label_text, val in [("重试", "retry"), ("跳过", "skip"), ("重新规划", "replan"), ("中止", "abort")]:
                tk.Button(btn_frame, text=label_text, command=lambda v=val: make_choice(v)).pack(side=tk.LEFT, padx=5)

            root.mainloop()
            return InterventionResult(
                type="button",
                choice=result_container.get("choice", "retry"),
                text=result_container.get("text") or None,
            )
        except Exception:
            # 降级到简单 messagebox
            choice = messagebox.askyesnocancel(
                "干预",
                f"步骤 {getattr(step, 'name', 'unknown')} 需要干预。\n错误: {error_info}\n\n是=重试, 否=跳过, 取消=重新规划"
            )
            if choice is True:
                return InterventionResult(type="button", choice="retry")
            elif choice is False:
                return InterventionResult(type="button", choice="skip")
            else:
                return InterventionResult(type="button", choice="replan")
