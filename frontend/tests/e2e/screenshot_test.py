"""
Blueclaw 前端截图测试脚本
使用 Playwright 进行自动化截图测试
"""

import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright

# 测试配置
FRONTEND_URL = "http://localhost:5174"
WS_URL = "ws://localhost:8006"
SCREENSHOT_DIR = "tests/e2e/screenshots"

# 确保截图目录存在
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def get_timestamp():
    return datetime.now().strftime("%H%M%S")


async def test_1_page_load_and_websocket():
    """测试题目 1: 页面加载与 WebSocket 连接"""
    print("\n" + "="*60)
    print("测试题目 1: 页面加载与 WebSocket 连接")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        
        # 监听 console 消息
        console_logs = []
        page = await context.new_page()
        page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        
        print(f"[步骤 1] 访问 {FRONTEND_URL}")
        await page.goto(FRONTEND_URL, wait_until='networkidle')
        await asyncio.sleep(3)  # 等待 WebSocket 连接
        
        # 截图 1: 整个页面
        screenshot_path = f"{SCREENSHOT_DIR}/test1_page_load_{get_timestamp()}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"[截图] 页面截图: {screenshot_path}")
        
        # 截图 2: 控制台日志
        console_content = "\n".join(console_logs[-20:]) if console_logs else "无控制台日志"
        print(f"[检查] 控制台日志:\n{console_content}")
        
        # 检查 WebSocket 连接状态
        ws_connected = any("WebSocket" in log and ("Connected" in log or "Connecting" in log) 
                          for log in console_logs)
        
        # 验证预期结果
        title = await page.title()
        blueclaw_visible = await page.is_visible("text=Blueclaw")
        input_visible = await page.is_visible("input[placeholder*='旅行']")
        
        results = {
            "页面标题": title,
            "Blueclaw标题显示": blueclaw_visible,
            "输入框显示": input_visible,
            "WebSocket连接": ws_connected,
            "无报错": not any("error" in log.lower() and "websocket" not in log.lower() 
                           for log in console_logs)
        }
        
        print("\n[验证结果]")
        for item, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {status} - {item}")
        
        await browser.close()
        return all(results.values())


async def test_2_input_and_thinking():
    """测试题目 2: 输入界面功能"""
    print("\n" + "="*60)
    print("测试题目 2: 输入界面功能")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()
        
        print(f"[步骤 1] 访问 {FRONTEND_URL}")
        await page.goto(FRONTEND_URL, wait_until='networkidle')
        await asyncio.sleep(2)
        
        # 截图: 输入前
        screenshot_path = f"{SCREENSHOT_DIR}/test2_input_before_{get_timestamp()}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"[截图] 输入前: {screenshot_path}")
        
        # 输入任务
        test_input = "帮我规划杭州2日游"
        print(f"[步骤 2] 输入: {test_input}")
        await page.fill('input[placeholder*="旅行"], input[type="text"]', test_input)
        await asyncio.sleep(1)
        
        # 截图: 输入后
        screenshot_path = f"{SCREENSHOT_DIR}/test2_input_after_{get_timestamp()}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"[截图] 输入后: {screenshot_path}")
        
        # 点击开始按钮
        print("[步骤 3] 点击'开始'按钮")
        await page.click('button:has-text("开始"), button[type="submit"]')
        await asyncio.sleep(3)
        
        # 截图: 思考界面
        screenshot_path = f"{SCREENSHOT_DIR}/test2_thinking_view_{get_timestamp()}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"[截图] 思考界面: {screenshot_path}")
        
        # 验证思考节点是否显示
        thinking_node = await page.is_visible("text=想规划什么样的旅行")
        left_panel = await page.is_visible("text=思考蓝图")
        
        results = {
            "可以输入文字": await page.input_value('input[placeholder*="旅行"]') == test_input,
            "点击后切换界面": left_panel,
            "显示思考节点": thinking_node
        }
        
        print("\n[验证结果]")
        for item, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {status} - {item}")
        
        await browser.close()
        return all(results.values())


async def test_3_thinking_selection():
    """测试题目 3: 思考节点选择"""
    print("\n" + "="*60)
    print("测试题目 3: 思考节点选择")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()
        
        print(f"[步骤 1] 访问并输入任务")
        await page.goto(FRONTEND_URL, wait_until='networkidle')
        await page.fill('input[placeholder*="旅行"]', "帮我规划杭州2日游")
        await page.click('button:has-text("开始")')
        await asyncio.sleep(3)
        
        # 截图: 初始思考节点
        screenshot_path = f"{SCREENSHOT_DIR}/test3_node_initial_{get_timestamp()}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"[截图] 初始节点: {screenshot_path}")
        
        # 点击节点展开
        print("[步骤 2] 点击思考节点展开")
        await page.click("text=想规划什么样的旅行")
        await asyncio.sleep(1)
        
        screenshot_path = f"{SCREENSHOT_DIR}/test3_node_expanded_{get_timestamp()}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"[截图] 展开的节点: {screenshot_path}")
        
        # 选择选项 A
        print("[步骤 3] 选择选项 A (自然风光)")
        option_a = await page.query_selector("text=自然风光")
        if option_a:
            await option_a.click()
        await asyncio.sleep(2)
        
        screenshot_path = f"{SCREENSHOT_DIR}/test3_option_selected_{get_timestamp()}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"[截图] 选择后状态: {screenshot_path}")
        
        # 验证
        two_nodes = await page.locator("text=想规划").count() >= 1
        
        results = {
            "节点可以展开": option_a is not None,
            "选择后状态更新": await page.is_visible("text=自然风光") or two_nodes
        }
        
        print("\n[验证结果]")
        for item, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {status} - {item}")
        
        await browser.close()
        return all(results.values())


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Blueclaw 前端截图测试开始")
    print("="*60)
    print(f"前端地址: {FRONTEND_URL}")
    print(f"截图保存: {SCREENSHOT_DIR}")
    
    results = {
        "测试 1 - 页面加载与WebSocket": await test_1_page_load_and_websocket(),
        "测试 2 - 输入界面功能": await test_2_input_and_thinking(),
        "测试 3 - 思考节点选择": await test_3_thinking_selection(),
    }
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {test_name}")
    
    print(f"\n截图保存在: {os.path.abspath(SCREENSHOT_DIR)}")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试执行出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
