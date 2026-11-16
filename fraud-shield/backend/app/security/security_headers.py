"""HTTP Security Headers Middleware.

Injects defense-in-depth headers into all HTTP responses to protect against
clickjacking, MIME-type sniffing, cross-site scripting (XSS), and data leakage.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces standard OWASP HTTP security headers on all API responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "object-src 'none'; "
                "frame-ancestors 'none';"
            )

        return response
