"""Tenant-bound browser behavior, plus a real Chromium acceptance fixture."""
import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace

import pytest

from chat.platform_context import ExecutionContext


class Control:
    def __init__(self):
        self.artifacts = []
        self.events = []

    def check_cancelled(self):
        return None

    def artifact(self, kind, **data):
        self.artifacts.append({"kind": kind, **data})
        return {"id": str(len(self.artifacts)), **self.artifacts[-1]}

    def event(self, kind, payload):
        self.events.append((kind, payload))


def context(tmp_path, user="alice", run="run1"):
    return ExecutionContext(user_id=user, workspace_id="personal", run_id=run,
                            workspace_root=str(tmp_path), control=Control())


class Page:
    url = "https://example.com/"
    text = "test content"

    def __init__(self):
        self.active = 0
        self.maximum = 0
        self.calls = []

    async def title(self):
        return "Example"

    async def goto(self, url, **kwargs):
        self.url = url
        return SimpleNamespace(status=200)

    async def inner_text(self, selector, **kwargs):
        return self.text

    async def content(self):
        return "<body>test content</body>"

    async def screenshot(self, **kwargs):
        return b"png"

    async def click(self, selector, **kwargs):
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(.02)
        self.calls.append(selector)
        self.active -= 1

    async def fill(self, selector, text, **kwargs):
        self.text = text

    async def is_closed(self):
        return False


class BrowserContext:
    def __init__(self):
        self.page = Page()
        self.pages = [self.page]
        self.routes = []
        self.closed = False

    async def new_page(self):
        return self.page

    async def route(self, pattern, handler):
        self.routes.append(handler)

    async def route_web_socket(self, pattern, handler):
        self.ws_handler = handler

    def on(self, *args):
        pass

    async def close(self):
        self.closed = True


class Browser:
    def __init__(self):
        self.contexts = []

    async def new_context(self, **kwargs):
        assert kwargs["service_workers"] == "block"
        ctx = BrowserContext()
        self.contexts.append(ctx)
        return ctx

    async def close(self):
        pass


def service(**kwargs):
    from worker.platform_browser import PlatformBrowser
    result = PlatformBrowser(testing=True, **kwargs)
    result._browser = Browser()
    return result


def test_sessions_are_owned_and_lost_after_restart(tmp_path):
    async def run():
        browser = service()
        first = await browser.execute(context(tmp_path), "ac", {"url": "https://example.com"})
        assert first["ok"]
        attack = await browser.execute(context(tmp_path, user="bob"), "oku", {"session_id": first["session_id"]})
        assert not attack["ok"] and attack["status"] == "session_lost"
        restarted = service()
        lost = await restarted.execute(context(tmp_path), "oku", {"session_id": first["session_id"]})
        assert not lost["ok"] and lost["status"] == "session_lost"
        await browser.kapat()
        await restarted.kapat()
    asyncio.run(run())


def test_capacity_does_not_evict_existing_session(tmp_path):
    async def run():
        browser = service(max_sessions=1)
        first = await browser.execute(context(tmp_path), "ac", {"url": "https://example.com"})
        second = await browser.execute(context(tmp_path, run="run2"), "ac", {"url": "https://example.com"})
        assert not second["ok"] and second["status"] == "capacity_wait"
        assert not browser._browser.contexts[0].closed
        assert (await browser.execute(context(tmp_path), "oku", {"session_id": first["session_id"]}))["ok"]
        await browser.kapat()
    asyncio.run(run())


def test_parallel_actions_on_same_session_are_serialized(tmp_path):
    async def run():
        browser = service()
        ctx = context(tmp_path)
        await browser.execute(ctx, "ac", {"url": "https://example.com"})
        results = await asyncio.gather(
            browser.execute(ctx, "tikla", {"selector": "#one"}),
            browser.execute(ctx, "tikla", {"selector": "#two"}),
        )
        assert all(item["ok"] for item in results)
        assert browser._browser.contexts[0].page.maximum == 1
        await browser.kapat()
    asyncio.run(run())


def test_dom_is_full_artifact_and_failed_postcondition_remains_failed(tmp_path):
    async def run():
        browser = service()
        ctx = context(tmp_path)
        await browser.execute(ctx, "ac", {"url": "https://example.com"})
        browser._browser.contexts[0].page.text = "large " * 10000
        read = await browser.execute(ctx, "oku", {})
        assert len(read["metin"]) > 20000
        assert any(item.get("content") == read["metin"] for item in ctx.control.artifacts)
        bad = await browser.execute(ctx, "dogrula", {"selector": "body", "expected": "missing"})
        assert bad["ok"] is False and bad["status"] == "check_failed"
        shot = await browser.execute(ctx, "ekran", {})
        assert shot["ok"]
        assert any(base64.b64decode(item.get("data_base64", "")) == b"png" for item in ctx.control.artifacts)
        await browser.kapat()
    asyncio.run(run())


def test_takeover_can_only_be_entered_from_user_channel(tmp_path):
    async def run():
        browser = service()
        ctx = context(tmp_path)
        await browser.execute(ctx, "ac", {"url": "https://example.com"})
        denied = await browser.execute(ctx, "devral", {})
        assert denied["status"] == "forbidden"
        assert (await browser.execute(ctx, "devral", {}, actor="user"))["ok"]
        blocked = await browser.execute(ctx, "tikla", {"selector": "#one"})
        assert blocked["status"] == "awaiting_user"
        assert (await browser.execute(ctx, "birak", {}, actor="user"))["ok"]
        assert (await browser.execute(ctx, "tikla", {"selector": "#one"}))["ok"]
        await browser.kapat()
    asyncio.run(run())


def test_upload_cannot_escape_workspace_and_guard_covers_subrequests(tmp_path):
    from worker.platform_browser import request_allowed, workspace_file
    assert request_allowed("http://127.0.0.1/admin") is False
    assert request_allowed("http://169.254.169.254/latest/meta-data") is False
    assert request_allowed("file:///etc/passwd") is False
    assert request_allowed("data:image/png;base64,aGVsbG8=") is True
    with pytest.raises(PermissionError):
        workspace_file(context(tmp_path), "../outside.txt")
    (tmp_path / ".env").write_text("secret", encoding="utf-8")
    with pytest.raises(PermissionError):
        workspace_file(context(tmp_path), ".env")


def test_production_wrapper_requires_isolated_cloud_worker(tmp_path, monkeypatch):
    from worker.platform_browser import execute_browser
    monkeypatch.delenv("BASAK_BROWSER_ISOLATED", raising=False)
    result = execute_browser(context(tmp_path), "ac", {"url": "https://example.com"})
    assert result["ok"] is False and result["status"] == "browser_unavailable"


def test_real_chromium_form_upload_download_and_full_snapshot(tmp_path):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    from playwright.async_api import async_playwright
    from worker.platform_browser import PlatformBrowser

    with asyncio.Runner() as runner:
        async def installed():
            async with async_playwright() as pw:
                return Path(pw.chromium.executable_path).is_file()
        if not runner.run(installed()):
            pytest.skip("Chromium is not installed")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/download":
                self.send_response(200)
                self.send_header("Content-Disposition", 'attachment; filename="result.txt"')
                self.end_headers()
                self.wfile.write(b"verified download")
                return
            body = b'''<html><title>Fixture</title><body>
            <input id="name"><button id="send" onclick="document.querySelector('#result').textContent=document.querySelector('#name').value">Save</button>
            <p id="result">empty</p><input id="file" type="file"><a id="download" href="/download">Download</a></body></html>'''
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (tmp_path / "upload.txt").write_text("upload fixture", encoding="utf-8")

    async def run():
        browser = PlatformBrowser(testing=True)
        ctx = context(tmp_path)
        try:
            assert (await browser.execute(ctx, "ac", {"url": "http://127.0.0.1:%s" % server.server_port}))["ok"]
            assert (await browser.execute(ctx, "yaz", {"selector": "#name", "text": "Saved correctly"}))["ok"]
            assert (await browser.execute(ctx, "tikla", {"selector": "#send"}))["ok"]
            assert (await browser.execute(ctx, "dogrula", {"selector": "#result", "expected": "Saved correctly", "exact": True}))["ok"]
            assert (await browser.execute(ctx, "yukle", {"selector": "#file", "path": "upload.txt"}))["ok"]
            result = await browser.execute(ctx, "indir", {"selector": "#download"})
            assert result["ok"]
            assert any(base64.b64decode(item.get("data_base64", "")) == b"verified download" for item in ctx.control.artifacts)
            assert (await browser.execute(ctx, "ekran", {}))["ok"]
            assert any(item["kind"] == "browser" for item in ctx.control.artifacts)
        finally:
            await browser.kapat()
    try:
        asyncio.run(run())
    finally:
        server.shutdown()
        server.server_close()


def test_browser_guards_private_redirects_subrequests_and_websockets(tmp_path):
    class Route:
        def __init__(self, url):
            self.request = SimpleNamespace(url=url)
            self.outcome = None
        async def continue_(self):
            self.outcome = 'allowed'
        async def abort(self):
            self.outcome = 'blocked'

    class WebSocketRoute:
        def __init__(self, url):
            self.url = url
            self.outcome = None
        async def connect(self):
            self.outcome = 'allowed'
        async def close(self):
            self.outcome = 'blocked'

    async def run():
        browser = service()
        try:
            first = await browser.execute(context(tmp_path), 'ac',
                                          {'url': 'https://example.com'})
            assert first['ok']
            fake = browser._browser.contexts[0]
            assert fake.routes, 'all requests must pass the network guard'
            for url in ('http://127.0.0.1/admin',
                        'http://169.254.169.254/latest/meta-data',
                        'file:///etc/passwd'):
                intercepted = Route(url)
                await fake.routes[0](intercepted)
                assert intercepted.outcome == 'blocked'
            websocket = WebSocketRoute('ws://127.0.0.1/secrets')
            await fake.ws_handler(websocket)
            assert websocket.outcome == 'blocked'
        finally:
            await browser.kapat()
    asyncio.run(run())

def test_successful_browser_postcondition_returns_verification_evidence(tmp_path):
    async def run():
        browser = service()
        try:
            ctx = context(tmp_path)
            assert (await browser.execute(ctx, 'ac', {'url': 'https://example.com'}))['ok']
            passed = await browser.execute(ctx, 'dogrula',
                                           {'selector': 'body', 'expected': 'test content'})
            assert passed['ok'] is True and passed['verified'] is True
            failed = await browser.execute(ctx, 'dogrula',
                                           {'selector': 'body', 'expected': 'not present'})
            assert failed['ok'] is False
            assert failed.get('verified') is not True
        finally:
            await browser.kapat()
    asyncio.run(run())


def test_sync_browser_wrapper_preserves_event_loop_between_actions(tmp_path, monkeypatch):
    from worker import platform_browser as module

    class FixtureBrowser:
        def __init__(self, testing=False):
            self.owner_loop = None
            self.calls = []
        async def execute(self, ctx, operation, args=None, actor=None):
            current_loop = asyncio.get_running_loop()
            if self.owner_loop is None:
                self.owner_loop = current_loop
            assert current_loop is self.owner_loop
            self.calls.append(operation)
            return {'ok': True, 'status': 'ok'}
        async def kapat(self):
            pass

    monkeypatch.setenv('BASAK_BROWSER_ISOLATED', '1')
    module._shutdown_service()
    monkeypatch.setattr(module, 'PlatformBrowser', FixtureBrowser)
    ctx = context(tmp_path)
    try:
        assert module.execute_browser(ctx, 'ac', {'url': 'https://example.com'})['ok']
        instance = module._SERVICE
        assert module.execute_browser(ctx, 'yaz', {'selector': '#field', 'text': 'hello'})['ok']
        assert module.execute_browser(ctx, 'tikla', {'selector': '#submit'})['ok']
        assert instance.calls == ['ac', 'yaz', 'tikla']
    finally:
        module._shutdown_service()
