import contextvars
import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

CORRELATION_ID_HEADER = "x-correlation-id"

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


class CorrelationIDMiddleware:
    """
    Pure ASGI middleware (no BaseHTTPMiddleware / anyio tasks).
    Avoids asyncpg 'Future attached to different loop' errors caused by
    anyio task-group spawning inside BaseHTTPMiddleware.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        correlation_id = next(
            (v.decode() for k, v in raw_headers if k == b"x-correlation-id"),
            str(uuid.uuid4()),
        )
        token = _correlation_id_var.set(correlation_id)

        async def send_with_cid(message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-correlation-id", correlation_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_cid)
        finally:
            _correlation_id_var.reset(token)


def get_correlation_id() -> str:
    return _correlation_id_var.get()
