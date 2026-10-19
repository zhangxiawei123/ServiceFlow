"""Render-only entry point. Secrets must be configured in the dashboard."""

import os
from pathlib import Path

from deploy.demo_gateway import create_gateway


password = os.environ.get("SERVICEFLOW_DEMO_PASSWORD", "")
if len(password) < 12:
    raise RuntimeError("Set SERVICEFLOW_DEMO_PASSWORD (at least 12 characters) in Render")
if not os.environ.get("REDIS_URL"):
    raise RuntimeError("Set REDIS_URL to the Render Key Value internal connection URL")

from api import main as backend_module  # noqa: E402


async def check_storage_ready():
    memory = backend_module._memory
    if memory is None or not await memory._redis.ping():
        raise RuntimeError("Working memory is unavailable")

app = create_gateway(
    backend_module.app,
    password=password,
    username=os.environ.get("SERVICEFLOW_DEMO_USERNAME", "demo"),
    hourly_limit=int(os.environ.get("SERVICEFLOW_CHAT_LIMIT_PER_HOUR", "30")),
    frontend_dir=Path(__file__).resolve().parent.parent / "frontend",
    readiness_check=check_storage_ready,
)
