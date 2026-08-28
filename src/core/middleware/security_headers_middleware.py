"""Security response headers middleware."""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attaches standard HTTP security headers to every response.

    Headers applied
    ---------------
    X-Content-Type-Options     — prevents MIME-type sniffing
    X-Frame-Options            — prevents clickjacking
    Content-Security-Policy    — restricts resource loading (strict API-safe policy)
    Strict-Transport-Security  — enforces HTTPS (only meaningful in production/TLS)
    X-XSS-Protection           — legacy browser XSS filter (belt-and-suspenders)
    Referrer-Policy            — limits referrer header leakage
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        # HSTS — only meaningful over TLS (Render terminates TLS at edge)
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        return response
