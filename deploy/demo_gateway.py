"""Password-protected, single-worker gateway for a small public demo."""

import asyncio
import base64
import binascii
import hmac
import json
import re
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import ClientDisconnect, Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route


class DemoGateway:
    """Bound demo traffic before it reaches the model or privileged API routes.

    Limits are shared by all visitors in this process and reset on restart.
    The deployment must use one worker. This is not multi-user authentication.
    """

    def __init__(self, app, *, password, username="demo", hourly_limit=30):
        if len(password) < 12:
            raise ValueError("SERVICEFLOW_DEMO_PASSWORD must contain at least 12 characters")
        if hourly_limit < 1:
            raise ValueError("SERVICEFLOW_CHAT_LIMIT_PER_HOUR must be positive")
        self.app = app
        self._credentials = f"{username}:{password}".encode("utf-8")
        self._hourly_limit = hourly_limit
        self._chat_times = deque()
        self._chat_busy = False

    async def _error(self, scope, receive, send, status, detail, headers=None):
        response = JSONResponse(
            {"detail": detail}, status_code=status,
            headers={"Cache-Control": "no-store", **(headers or {})},
        )
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path, method = scope["path"], scope["method"]
        # Render probes this route without credentials. It contains no stats.
        if path == "/healthz" and method in {"GET", "HEAD"}:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        try:
            supplied = base64.b64decode(token, validate=True) if scheme.lower() == "basic" else b""
        except (binascii.Error, ValueError):
            supplied = b""
        if not hmac.compare_digest(supplied, self._credentials):
            await self._error(scope, receive, send, 401, "请使用演示访问口令登录", {
                "WWW-Authenticate": 'Basic realm="ServiceFlow demo", charset="UTF-8"',
            })
            return

        read_allowed = path in {"/", "/styles.css", "/app.js", "/health"}
        read_allowed = read_allowed or bool(re.fullmatch(r"/trace/tool/[A-Za-z0-9_-]{1,64}", path))
        is_chat = path == "/chat" and method == "POST"
        if not (is_chat or (read_allowed and method in {"GET", "HEAD"})):
            await self._error(scope, receive, send, 404, "演示环境未开放此接口")
            return
        if not is_chat:
            await self.app(scope, receive, send)
            return

        if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
            await self._error(scope, receive, send, 415, "请使用 application/json")
            return
        body = bytearray()
        try:
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 16_384:
                    await self._error(scope, receive, send, 413, "请求体过大")
                    return
        except ClientDisconnect:
            return
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            payload = None
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, str) or not message.strip() or len(message) > 2000:
            await self._error(scope, receive, send, 422, "消息须为 1 到 2000 字的文本")
            return

        now = time.monotonic()
        while self._chat_times and self._chat_times[0] <= now - 3600:
            self._chat_times.popleft()
        if self._chat_busy or len(self._chat_times) >= self._hourly_limit:
            await self._error(scope, receive, send, 429, "演示服务繁忙或已达每小时额度，请稍后重试", {
                "Retry-After": "60",
            })
            return

        # No await between checking and reserving the slot (one event loop).
        self._chat_busy = True
        self._chat_times.append(now)
        body_sent = False

        async def replay_receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        try:
            await self.app(scope, replay_receive, send)
        finally:
            self._chat_busy = False


def create_gateway(backend, *, password, frontend_dir, username="demo", hourly_limit=30, readiness_check=None):
    frontend = Path(frontend_dir)
    assets = {"/": "index.html", "/styles.css": "styles.css", "/app.js": "app.js"}

    async def serve_frontend(request):
        return FileResponse(frontend / assets[request.url.path], headers={"Cache-Control": "no-store"})

    async def readiness(request):
        if readiness_check is not None:
            try:
                await asyncio.wait_for(readiness_check(), timeout=3)
            except Exception:
                return JSONResponse({"status": "unavailable"}, status_code=503,
                                    headers={"Cache-Control": "no-store"})
        return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})

    @asynccontextmanager
    async def lifespan(app):
        # Mounted applications do not automatically receive startup/shutdown.
        async with backend.router.lifespan_context(backend):
            yield

    public_app = Starlette(
        routes=[Route(path, serve_frontend) for path in assets] + [
            Route("/healthz", readiness), Mount("/", app=backend),
        ],
        lifespan=lifespan,
    )
    return DemoGateway(public_app, password=password, username=username, hourly_limit=hourly_limit)
