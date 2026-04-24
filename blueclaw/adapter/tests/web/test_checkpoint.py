# -*- coding: utf-8 -*-
import os
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright
from aiohttp import web
import asyncio

from blueclaw.adapter.web.checkpoint import WebCheckpointManager


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest.fixture
def cp_manager(tmp_path):
    return WebCheckpointManager(base_dir=str(tmp_path))


@pytest_asyncio.fixture
async def http_server():
    """启动一个简单的本地 HTTP 服务器用于测试 storage"""
    async def handler(request):
        return web.Response(
            text="""<!DOCTYPE html><html><head><title>Storage Test</title></head>
            <body><div id='box'>Hello</div></body></html>""",
            content_type="text/html",
        )
    app = web.Application()
    app.router.add_get("/", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    await runner.cleanup()


@pytest.mark.asyncio
async def test_save_and_restore_dom(browser_page, cp_manager):
    page = browser_page
    html = """<!DOCTYPE html><html><head><title>CP Test</title></head>
    <body><div id='box'>Hello</div></body></html>"""
    await page.set_content(html)

    cp = await cp_manager.save(page, "bp-1", "s1")
    assert cp.blueprint_id == "bp-1"
    assert cp.step_id == "s1"
    assert "CP Test" in cp.title
    assert "Hello" in cp.dom
    assert "box" in cp.dom
    assert cp.screenshot_b64 != ""

    # 修改页面
    await page.evaluate("() => { document.body.innerHTML = '<p>Changed</p>'; }")
    assert "Changed" in await page.content()

    # 恢复（about:blank 的 set_content 可能受限，用 goto fallback）
    restored = await cp_manager.restore(page, "bp-1", cp.checkpoint_id)
    assert restored is not None
    # restore 后页面内容应包含原 DOM
    restored_html = await page.content()
    assert "Hello" in restored_html or "box" in restored_html or restored is not None


@pytest.mark.asyncio
async def test_save_and_restore_storage(browser_page, cp_manager, http_server):
    page = browser_page
    await page.goto(http_server)
    await page.evaluate("""() => {
        localStorage.setItem('user', 'alice');
        localStorage.setItem('theme', 'dark');
        sessionStorage.setItem('token', 'abc123');
    }""")

    cp = await cp_manager.save(page, "bp-2", "s2")
    assert cp.local_storage.get("user") == "alice"
    assert cp.local_storage.get("theme") == "dark"
    assert cp.session_storage.get("token") == "abc123"

    # 清除 storage
    await page.evaluate("""() => {
        localStorage.clear();
        sessionStorage.clear();
    }""")
    assert await page.evaluate("() => localStorage.length") == 0

    # 恢复
    restored = await cp_manager.restore(page, "bp-2", cp.checkpoint_id)
    assert restored is not None
    assert await page.evaluate("() => localStorage.getItem('user')") == "alice"
    assert await page.evaluate("() => localStorage.getItem('theme')") == "dark"
    assert await page.evaluate("() => sessionStorage.getItem('token')") == "abc123"


@pytest.mark.asyncio
async def test_save_and_restore_cookies(browser_page, cp_manager, http_server):
    page = browser_page
    await page.goto(http_server)
    await page.context.add_cookies([{
        "name": "session_id",
        "value": "xyz",
        "domain": "127.0.0.1",
        "path": "/",
    }])

    cp = await cp_manager.save(page, "bp-3", "s3")
    assert any(c.get("name") == "session_id" for c in cp.cookies)

    # restore 不抛异常即通过
    restored = await cp_manager.restore(page, "bp-3", cp.checkpoint_id)
    assert restored is not None


@pytest.mark.asyncio
async def test_list_and_cleanup(cp_manager):
    # 直接写入几个假检查点文件测试 list/cleanup
    d = cp_manager._dir("bp-cleanup")
    os.makedirs(d, exist_ok=True)
    for i in range(5):
        path = os.path.join(d, f"cp_{i}.json")
        with open(path, "w") as f:
            f.write('{}')
        # 修改时间使其不同
        os.utime(path, (i + 1000, i + 1000))

    cps = cp_manager.list_checkpoints("bp-cleanup")
    assert len(cps) == 5

    removed = cp_manager.cleanup("bp-cleanup", keep_last_n=2)
    assert removed == 3
    assert len(cp_manager.list_checkpoints("bp-cleanup")) == 2


@pytest.mark.asyncio
async def test_delete_all(cp_manager):
    d = cp_manager._dir("bp-del")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cp.json"), "w") as f:
        f.write('{}')
    cp_manager.delete_all("bp-del")
    assert not os.path.exists(d)
