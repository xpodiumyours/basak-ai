"""Tenant-bound Chromium. Workers execute; they do not plan."""
import asyncio
import base64
import ipaddress
import os
import socket
import threading
import uuid
from pathlib import Path
from urllib.parse import urlparse

_BLOCKED_NAMES = {".env", "ayarlar.json"}
_BLOCKED_SUFFIX = (".pem", ".key")


def request_allowed(url):
    try:
        parsed = urlparse(str(url or ""))
    except ValueError:
        return False
    if parsed.scheme == "data":
        return True
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host or host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        rows = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, ValueError, OSError):
        return False
    if not rows:
        return False
    for row in rows:
        ip = ipaddress.ip_address(row[4][0])
        if not ip.is_global:
            return False
    return True


def workspace_file(ctx, relative):
    root = Path(getattr(ctx, "workspace_root", "") or "").resolve()
    if not root.is_dir():
        raise PermissionError("Calisma alani yok")
    rel = str(relative or "").replace("\\", "/")
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise PermissionError("Dosya calisma alaninin disinda")
    name = Path(rel).name
    if name in _BLOCKED_NAMES or name.endswith(_BLOCKED_SUFFIX) or name.startswith("."):
        raise PermissionError("Bu dosya uygulama tarafindan yonetilir")
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise PermissionError("Dosya calisma alaninin disinda")
    return path


def _fail(status, **extra):
    body = {"ok": False, "status": status}
    body.update(extra)
    return body


def _ok(**extra):
    body = {"ok": True, "status": "ok"}
    body.update(extra)
    return body


class PlatformBrowser:
    def __init__(self, testing=False, max_sessions=8):
        self.testing = bool(testing)
        self.max_sessions = max(1, int(max_sessions))
        self._browser = None
        self._playwright = None
        self._sessions = {}
        self._locks = {}
        self._loop_lock = threading.Lock()

    def _session_for(self, ctx, args):
        sid = str((args or {}).get("session_id") or "")
        if sid:
            sess = self._sessions.get(sid)
            if not sess or sess["user_id"] != ctx.user_id:
                return None
            return sess
        for sess in self._sessions.values():
            if sess["user_id"] == ctx.user_id and sess["run_id"] == ctx.run_id:
                return sess
        return None

    async def _ensure_browser(self):
        if self._browser is not None:
            return self._browser
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def _page(self, sess):
        ctx = sess["context"]
        pages = getattr(ctx, "pages", None) or []
        if pages:
            return pages[0]
        return await ctx.new_page()

    async def execute(self, ctx, islem, args=None, actor=None):
        args = dict(args or {})
        islem = str(islem or "")
        actor = str(actor or "agent")
        if islem == "ac":
            if len(self._sessions) >= self.max_sessions:
                return _fail("capacity_wait")
            url = str(args.get("url") or "")
            local_ok = self.testing and (urlparse(url).hostname in ("127.0.0.1", "localhost"))
            if not url or not (request_allowed(url) or local_ok):
                return _fail("blocked_url")
            browser = await self._ensure_browser()
            context = await browser.new_context(
                accept_downloads=True, service_workers="block")

            def allowed_destination(destination):
                parsed = urlparse(str(destination or ""))
                local_fixture = self.testing and parsed.hostname in ("127.0.0.1", "localhost")
                return local_fixture or request_allowed(destination)

            async def guard_request(route):
                # Apply the same policy to redirects, iframes and subresources.
                if allowed_destination(route.request.url):
                    await route.continue_()
                else:
                    await route.abort()

            async def guard_websocket(route):
                # WS URLs require their own guard; no implicit intranet access.
                parsed = urlparse(str(route.url))
                http_scheme = "https" if parsed.scheme == "wss" else "http"
                allowed = parsed.scheme in ("wss", "ws") and allowed_destination(
                    parsed._replace(scheme=http_scheme).geturl())
                if allowed:
                    await route.connect()
                else:
                    await route.close()

            await context.route("**/*", guard_request)
            await context.route_web_socket("**/*", guard_websocket)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            sid = uuid.uuid4().hex
            lock = asyncio.Lock()
            self._locks[sid] = lock
            self._sessions[sid] = {
                "id": sid, "user_id": ctx.user_id, "run_id": ctx.run_id,
                "workspace_id": ctx.workspace_id, "context": context,
                "takeover": False,
            }
            return _ok(session_id=sid, url=getattr(page, "url", url))

        sess = self._session_for(ctx, args)
        if sess is None:
            return _fail("session_lost")
        if islem == "devral":
            if actor != "user":
                return _fail("forbidden")
            sess["takeover"] = True
            return _ok(session_id=sess["id"])
        if islem == "birak":
            if actor != "user":
                return _fail("forbidden")
            sess["takeover"] = False
            return _ok(session_id=sess["id"])
        if sess["takeover"] and actor != "user":
            return _fail("awaiting_user")

        lock = self._locks.setdefault(sess["id"], asyncio.Lock())
        async with lock:
            return await self._act(ctx, sess, islem, args)

    async def _act(self, ctx, sess, islem, args):
        page = await self._page(sess)
        control = getattr(ctx, "control", None)
        if islem == "oku":
            selector = str(args.get("selector") or "body")
            metin = await page.inner_text(selector)
            html = await page.content()
            if control is not None:
                control.artifact("browser", title=getattr(page, "url", ""), content=metin,
                                 html=html, mime_type="text/plain")
            return _ok(session_id=sess["id"], metin=metin, url=getattr(page, "url", ""))
        if islem == "tikla":
            await page.click(str(args.get("selector") or "body"))
            return _ok(session_id=sess["id"])
        if islem == "yaz":
            await page.fill(str(args.get("selector") or "input"), str(args.get("text") or ""))
            return _ok(session_id=sess["id"])
        if islem == "tus":
            await page.keyboard.press(str(args.get("key") or "Enter"))
            return _ok(session_id=sess["id"])
        if islem == "kaydir":
            await page.mouse.wheel(0, int(args.get("delta") or 600))
            return _ok(session_id=sess["id"])
        if islem == "dogrula":
            selector = str(args.get("selector") or "body")
            expected = str(args.get("expected") or "")
            text = await page.inner_text(selector)
            exact = bool(args.get("exact"))
            ok = text == expected if exact else expected in text
            if not ok:
                return _fail("check_failed", found=text, expected=expected)
            return _ok(session_id=sess["id"], found=text)
        if islem == "ekran":
            png = await page.screenshot(full_page=True)
            if control is not None:
                control.artifact("browser", title="screenshot",
                                 data_base64=base64.b64encode(png).decode(),
                                 mime_type="image/png")
            return _ok(session_id=sess["id"], data_base64=base64.b64encode(png).decode())
        if islem == "yukle":
            path = workspace_file(ctx, args.get("path"))
            await page.set_input_files(str(args.get("selector") or "input[type=file]"), str(path))
            return _ok(session_id=sess["id"])
        if islem == "indir":
            async with page.expect_download() as pending:
                await page.click(str(args.get("selector") or "a"))
            download = await pending.value
            body = Path(await download.path()).read_bytes()
            if control is not None:
                control.artifact("browser", title=download.suggested_filename,
                                 data_base64=base64.b64encode(body).decode(),
                                 mime_type="application/octet-stream")
            return _ok(session_id=sess["id"], bytes=len(body))
        return _fail("unknown_action")

    async def kapat(self):
        for sess in list(self._sessions.values()):
            closer = getattr(sess["context"], "close", None)
            if callable(closer):
                result = closer()
                if asyncio.iscoroutine(result):
                    await result
        self._sessions.clear()
        if self._browser is not None and hasattr(self._browser, "close"):
            result = self._browser.close()
            if asyncio.iscoroutine(result):
                await result
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        self._browser = None


_SERVICE = None
_SERVICE_LOCK = threading.Lock()


def execute_browser(ctx, islem, args=None, actor=None):
    if not os.environ.get("BASAK_BROWSER_ISOLATED"):
        return _fail("browser_unavailable")
    async def run():
        global _SERVICE
        with _SERVICE_LOCK:
            service = _SERVICE
            if service is None:
                service = PlatformBrowser(testing=False)
                _SERVICE = service
        return await service.execute(ctx, islem, args, actor=actor)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run())
    raise RuntimeError("Aktif async dongude bulut tarayicisi await edilmeli")
