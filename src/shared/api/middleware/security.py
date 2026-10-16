from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

_CONTENT_SECURITY_POLICY = "default-src 'none'; frame-ancestors 'none'"

# Swagger UI e ReDoc carregam scripts/CSS de CDNs e não funcionam sob a CSP restritiva.
_CSP_EXEMPT_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/redoc"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que injeta cabeçalhos HTTP de segurança seguindo as recomendações OWASP.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path not in _CSP_EXEMPT_PATHS:
            response.headers["Content-Security-Policy"] = _CONTENT_SECURITY_POLICY

        return response
