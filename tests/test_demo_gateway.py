import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from deploy.demo_gateway import create_gateway


PASSWORD = "test-demo-password-only"
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def make_demo(*, endpoint=None, hourly_limit=30, lifespan=None):
    async def echo(request):
        if request.method == "POST":
            return JSONResponse(await request.json())
        return JSONResponse({"status": "ok"})

    backend = Starlette(routes=[
        Route("/chat", endpoint or echo, methods=["POST"]),
        Route("/health", echo),
        Route("/eval/run", echo, methods=["POST"]),
        Route("/knowledge/upload", echo, methods=["POST"]),
        Route("/trace/tools", echo),
        Route("/trace/tool/{request_id}", echo),
    ], lifespan=lifespan)
    return create_gateway(backend, password=PASSWORD, frontend_dir=FRONTEND, hourly_limit=hourly_limit)


def test_health_probe_and_login_page_are_public_but_api_requires_password():
    with TestClient(make_demo()) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        landing = client.get("/")
        assert landing.status_code == 200
        assert 'id="login-form"' in landing.text
        assert "www-authenticate" not in landing.headers
        for path in ["/app.js", "/health"]:
            response = client.get(path)
            assert response.status_code == 401
            assert "www-authenticate" not in response.headers
        assert client.get("/app.js", auth=("demo", "wrong-password")).status_code == 401
        assert client.get("/app.js", headers={"Authorization": "Basic !!!"}).status_code == 401


def test_browser_login_uses_secure_cookie_without_native_auth_dialog():
    with TestClient(make_demo(), base_url="https://demo.test") as client:
        assert client.post("/login", json={"password": "wrong"}).status_code == 401
        response = client.post("/login", json={"username": "demo", "password": PASSWORD},
                               headers={"Origin": "https://demo.test"})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        for attribute in ["secure", "httponly", "samesite=strict", "path=/", "max-age=28800"]:
            assert attribute in cookie
        assert "www-authenticate" not in response.headers
        assert PASSWORD not in response.text
        assert 'id="login-form"' not in client.get("/").text
        assert client.get("/app.js").status_code == 200
        assert client.post("/chat", json={"message": "hello"},
                           headers={"Origin": "https://demo.test"}).status_code == 200
        assert client.get("/docs").status_code == 404


def test_login_and_cookie_authenticated_chat_reject_cross_site_requests():
    with TestClient(make_demo(), base_url="https://demo.test") as client:
        credentials = {"password": PASSWORD}
        assert client.post("/login", json=credentials, headers={"Origin": "https://evil.test"}).status_code == 403
        assert client.post("/login", json=credentials).status_code == 200
        assert client.post("/chat", json={"message": "hello"}, headers={"Origin": "https://evil.test"}).status_code == 403
        assert client.post("/chat", json={"message": "hello"}, headers={"Origin": "null"}).status_code == 403


def test_expired_forged_and_previous_process_cookies_do_not_authenticate():
    demo = make_demo()
    with TestClient(demo, base_url="https://demo.test") as client:
        client.post("/login", json={"password": PASSWORD})
        token = client.cookies.get(demo.COOKIE_NAME)
        for invalid in [token[:-1] + ("a" if token[-1] != "a" else "b"), "0.nonce.signature", "bad", "1.n.非ASCII"]:
            assert not demo._valid_session(invalid)
        assert not make_demo()._valid_session(token)
        client.cookies.clear()
        assert client.get("/health").status_code == 401


def test_login_rate_and_body_limits_apply_before_backend():
    with TestClient(make_demo()) as client:
        assert client.post("/login", content="x").status_code == 415
        assert client.post("/login", json={"password": "x" * 5000}).status_code == 413
        assert client.post("/login", content="invalid", headers={"Content-Type": "application/json"}).status_code == 422
        for _ in range(7):
            assert client.post("/login", json={"password": "wrong"}).status_code == 401
        assert client.post("/login", json={"password": PASSWORD}).status_code == 429


def test_frontend_assets_and_chat_share_one_authenticated_origin():
    with TestClient(make_demo()) as client:
        client.auth = ("demo", PASSWORD)
        assert "<!doctype html>" in client.get("/").text.lower()
        assert "sendMessage" in client.get("/app.js").text
        assert client.get("/styles.css").status_code == 200
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/chat", json={"message": "你好", "conv_id": "c1"})
        assert response.status_code == 200
        assert response.json()["conv_id"] == "c1"
        assert client.get("/trace/tool/abc123").status_code == 200


@pytest.mark.parametrize("path,method", [
    ("/eval/run", "POST"), ("/knowledge/upload", "POST"),
    ("/skills/reload", "POST"), ("/trace/tools", "GET"),
    ("/docs", "GET"), ("/openapi.json", "GET"), ("/metrics", "GET"),
])
def test_management_routes_are_not_published_even_with_demo_password(path, method):
    with TestClient(make_demo()) as client:
        assert client.request(method, path, auth=("demo", PASSWORD)).status_code == 404


def test_invalid_or_large_messages_are_rejected_before_calling_backend():
    with TestClient(make_demo()) as client:
        client.auth = ("demo", PASSWORD)
        for message in ["", "   ", "x" * 2001, 123]:
            assert client.post("/chat", json={"message": message}).status_code == 422
        assert client.post("/chat", content="invalid", headers={"Content-Type": "application/json"}).status_code == 422
        assert client.post("/chat", json={"message": "x" * 17_000}).status_code == 413
        assert client.post("/chat", content="message=hello").status_code == 415
        assert client.post("/chat", json={"message": "有效请求"}).status_code == 200


def test_hourly_quota_is_shared_between_visitors():
    with TestClient(make_demo(hourly_limit=1)) as client:
        client.auth = ("demo", PASSWORD)
        assert client.post("/chat", json={"message": "一", "user_id": "a"}).status_code == 200
        response = client.post("/chat", json={"message": "二", "user_id": "b"})
        assert response.status_code == 429
        assert "retry-after" in response.headers


def test_only_one_chat_runs_at_a_time_and_slot_is_released():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def slow_chat(request):
            entered.set()
            await release.wait()
            return JSONResponse({"response": "ok"})

        transport = httpx.ASGITransport(app=make_demo(endpoint=slow_chat))
        async with httpx.AsyncClient(transport=transport, base_url="http://test", auth=("demo", PASSWORD)) as client:
            first = asyncio.create_task(client.post("/chat", json={"message": "first"}))
            await asyncio.wait_for(entered.wait(), timeout=2)
            try:
                assert (await client.post("/chat", json={"message": "second"})).status_code == 429
            finally:
                release.set()
                assert (await first).status_code == 200
            assert (await client.post("/chat", json={"message": "third"})).status_code == 200

    asyncio.run(scenario())


def test_backend_lifespan_is_forwarded():
    events = []

    @asynccontextmanager
    async def lifespan(app):
        events.append("startup")
        yield
        events.append("shutdown")

    with TestClient(make_demo(lifespan=lifespan)) as client:
        assert events == ["startup"]
        assert client.get("/healthz").status_code == 200
    assert events == ["startup", "shutdown"]


def test_missing_password_fails_closed():
    with pytest.raises(ValueError, match="PASSWORD"):
        create_gateway(Starlette(), password="", frontend_dir=FRONTEND)


def test_health_probe_checks_storage_without_exposing_connection_details():
    async def broken_storage():
        raise RuntimeError("private connection detail must not be returned")

    demo = create_gateway(Starlette(), password=PASSWORD, frontend_dir=FRONTEND,
                          readiness_check=broken_storage)
    with TestClient(demo) as client:
        response = client.get("/healthz")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
