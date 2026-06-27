"""Production ASGI application around the Streamable HTTP MCP transport."""

import contextlib
import logging
from uuid import uuid4

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

import retail_mcp.server as server_module
from retail_mcp.errors import RetailMCPError
from retail_mcp.metrics import IN_FLIGHT, REQUESTS
from retail_mcp.security import (
    TokenBucketRateLimiter,
    reset_request_context,
    set_request_context,
)
from retail_mcp.server import authentication, mcp, settings

logger = logging.getLogger(__name__)
rate_limiter = TokenBucketRateLimiter(settings.rate_limit_per_minute)


class ApiKeyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_key = headers.get(b"x-api-key")
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        api_key = raw_key.decode("latin-1") if raw_key else None
        if not api_key and authorization.lower().startswith("bearer "):
            api_key = authorization[7:].strip()
        request_id = headers.get(b"x-request-id", uuid4().hex.encode()).decode("latin-1")[:64]
        try:
            principal = authentication.authenticate(api_key)
            rate_limiter.check(principal.subject)
        except RetailMCPError as exc:
            REQUESTS.labels("transport.authentication", "failure").inc()
            response = JSONResponse(
                {"error": exc.code, "message": exc.public_message, "request_id": request_id},
                status_code=401 if exc.code == "authentication_failed" else 429,
            )
            await response(scope, receive, send)
            return

        tokens = set_request_context(principal, request_id)
        IN_FLIGHT.inc()
        try:
            await self.app(scope, receive, send)
        finally:
            IN_FLIGHT.dec()
            reset_request_context(tokens)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def secure_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"cache-control", b"no-store"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, secure_send)


async def live(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "live", "version": "1.0.0"})


async def ready(_request: Request) -> JSONResponse:
    container = server_module.runtime
    healthy = bool(container and await container.ready())
    return JSONResponse(
        {"status": "ready" if healthy else "not_ready"}, status_code=200 if healthy else 503
    )


async def metrics(_request: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@contextlib.asynccontextmanager
async def lifespan(_app: Starlette):
    async with mcp.session_manager.run():
        yield


protected_mcp = SecurityHeadersMiddleware(ApiKeyMiddleware(mcp.streamable_http_app()))

app = Starlette(
    debug=False,
    routes=[
        Route("/health/live", live),
        Route("/health/ready", ready),
        Route("/metrics", metrics),
        Mount("/mcp", app=protected_mcp),
    ],
    middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=["*"])],
    lifespan=lifespan,
)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


configure_logging()
