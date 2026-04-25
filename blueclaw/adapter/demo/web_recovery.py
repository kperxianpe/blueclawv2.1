# -*- coding: utf-8 -*-
"""
Demo: 表单填写 + 自动恢复（备用选择器重试）

场景：
1. 导航到注册页
2. 填写用户名和密码
3. 点击提交按钮 —— 初始选择器因页面结构变化而失效
4. RecoveryController 自动使用 fallback selector 成功恢复
5. 验证提交成功

运行: python -m blueclaw.adapter.demo.web_recovery
"""
import asyncio
import tempfile
import os

from playwright.async_api import async_playwright

from blueclaw.adapter.web.executor import WebExecutor
from blueclaw.adapter.web.checkpoint import WebCheckpointManager
from blueclaw.adapter.web.validator import WebValidator
from blueclaw.adapter.web.recovery import RecoveryController, RecoveryConfig
from blueclaw.adapter.web.visualization import CanvasMindVisualizer
from blueclaw.adapter.core.screenshot import PlaywrightScreenshot
from blueclaw.adapter.models import ExecutionStep, ActionDefinition, TargetDescription, ValidationRule


HTML_CONTENT = """<!DOCTYPE html>
<html>
<head><title>Register</title></head>
<body>
  <h1>注册账号</h1>
  <form id="reg-form">
    <input id="username" placeholder="用户名">
    <input id="password" type="password" placeholder="密码">
    <button id="submit-old" type="button" onclick="submitForm()">提交注册</button>
  </form>
  <div id="result"></div>
  <script>
    // 模拟页面结构变化：页面加载后立即替换按钮 ID
    (function() {
      var oldBtn = document.getElementById('submit-old');
      if (oldBtn) {
        var newBtn = document.createElement('button');
        newBtn.id = 'submit-new';
        newBtn.type = 'button';
        newBtn.textContent = '提交注册';
        newBtn.onclick = submitForm;
        oldBtn.parentNode.replaceChild(newBtn, oldBtn);
      }
    })();
    function submitForm() {
      document.getElementById('result').textContent = '注册成功！';
    }
  </script>
</body>
</html>
"""


async def main():
    tmpdir = tempfile.mkdtemp()
    html_path = os.path.join(tmpdir, "register.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)

    url = f"file:///{html_path.replace(os.sep, '/')}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        # 配置 RecoveryController：启用 fallback selector
        cp_mgr = WebCheckpointManager(base_dir=os.path.join(tmpdir, "checkpoints"))
        recovery = RecoveryController(
            web_checkpoint_manager=cp_mgr,
            config=RecoveryConfig(
                max_retries=0,
                fallback_selectors=["#submit-new"],
                enable_rollback=False,
            ),
        )
        executor = WebExecutor(
            screenshot_capture=PlaywrightScreenshot(),
            validator=WebValidator(),
            recovery_controller=recovery,
            visualizer=CanvasMindVisualizer(),
            web_checkpoint_manager=cp_mgr,
        )

        steps = [
            ExecutionStep(
                step_id="s1", name="Navigate",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic=url)),
            ),
            ExecutionStep(
                step_id="s2", name="Wait for page change",
                action=ActionDefinition(type="wait", params={"ms": 800}),
            ),
            ExecutionStep(
                step_id="s3", name="Fill Username",
                action=ActionDefinition(
                    type="input", target=TargetDescription(semantic="用户名"),
                    params={"value": "alice"},
                ),
            ),
            ExecutionStep(
                step_id="s4", name="Fill Password",
                action=ActionDefinition(
                    type="input", target=TargetDescription(semantic="密码"),
                    params={"value": "secret123"},
                ),
            ),
            ExecutionStep(
                step_id="s5", name="Click Submit",
                action=ActionDefinition(
                    type="click", target=TargetDescription(selector="#submit-old"),
                ),
            ),
            ExecutionStep(
                step_id="s6", name="Verify Success",
                action=ActionDefinition(type="wait", params={"ms": 500}),
                validation=ValidationRule(type="text_contains", expected={"selector": "#result", "text": "注册成功"}),
            ),
        ]

        print("[Task Start] Register account on test site")
        for i, step in enumerate(steps, 1):
            print(f"步骤 {i}/{len(steps)}: {step.name} ... ", end="", flush=True)
            result = await executor.execute_step(step, page, blueprint_id="demo-register")
            if result.status == "success" and "Recovered" in result.output:
                print(f"OK (recovered: {result.output})")
            elif result.status == "success":
                print("OK")
            else:
                print(f"FAIL ({result.output})")

        # 最终验证
        final_text = await page.locator("#result").inner_text()
        if "注册成功" in final_text:
            print("\n[Task Complete] Registration successful!")
        else:
            print(f"\n[Task Failed] Final result: {final_text}")

        await browser.close()

    # 清理
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
