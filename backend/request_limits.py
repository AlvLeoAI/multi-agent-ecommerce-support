"""
Request admission limits and CORS origin parsing.

`RequestBodyLimitMiddleware` bounds the bytes of every request body before routing or
JSON parsing, so field-level `max_length` checks never see an oversized payload.
"""

from __future__ import annotations

import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

MAX_REQUEST_BODY_BYTES = 64 * 1024

# The Streamlit frontend calls the API server-side, so browsers only need CORS for
# local development against the default Streamlit port.
DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:8501",
    "http://127.0.0.1:8501",
)


def parse_cors_origins(raw: str | None) -> list[str]:
    """
    Parse a comma-separated `CORS_ALLOWED_ORIGINS` value into exact origins.
    Wildcards are dropped: an allowlist must name each origin. An empty or
    wildcard-only value falls back to the local development defaults.
    """
    origins: list[str] = []
    for part in (raw or "").split(","):
        origin = part.strip().rstrip("/")
        if not origin:
            continue
        if "*" in origin:
            logger.warning("Ignoring wildcard CORS origin; list exact origins instead.")
            continue
        if origin not in origins:
            origins.append(origin)
    return origins or list(DEFAULT_CORS_ORIGINS)


class RequestBodyLimitMiddleware:
    """Reject any HTTP request whose body exceeds `max_body_bytes` with a 413."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = MAX_REQUEST_BODY_BYTES) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={"detail": f"Request body exceeds the {self.max_body_bytes}-byte limit."},
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # A declared length over the limit is refused without reading the body. A small,
        # missing or invalid declaration never exempts the actual bytes below.
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = 0
                if declared > self.max_body_bytes:
                    await self._reject(scope, receive, send)
                    return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_body_bytes:
                await self._reject(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def buffered_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, buffered_receive, send)
