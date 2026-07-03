from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings

_OPEN_PATHS = {"/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"}


class AccessKeyMiddleware(BaseHTTPMiddleware):
    """Optional single-key protection for all /api/* routes.
    Activated only when ACCESS_KEY env var is set."""

    async def dispatch(self, request: Request, call_next):
        if not settings.ACCESS_KEY:
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/api/") or path in _OPEN_PATHS:
            return await call_next(request)

        provided = (
            request.headers.get("X-Access-Key")
            or request.query_params.get("key")
            or request.cookies.get("access_key")
        )
        if provided != settings.ACCESS_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing access key."},
            )
        return await call_next(request)
