"""Use the port supplied by the cloud platform, with one bounded worker."""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "deploy.render_app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
        workers=1,
        limit_concurrency=16,
        timeout_keep_alive=5,
        server_header=False,
    )
