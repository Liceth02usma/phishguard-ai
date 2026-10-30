"""Middleware de la API (spec 012, FR-003).

RateLimiter: 30 análisis/min por clave e IP.
SecurityHeadersMiddleware: cabeceras de seguridad.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import RATE_LIMIT_POR_MINUTO
from .errors import ErrorDetail, ErrorEnvelope


class RateLimiter(BaseHTTPMiddleware):
    """Rate limiter in-memory: 30 análisis/min por API key e IP.

    Solo aplica a POST /api/analyses (AC-API-09).
    """

    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: object) -> Response:
        # Solo limitar POST /api/analyses
        path = request.url.path
        method = request.method
        if method != "POST" or path != "/api/analyses":
            return await call_next(request)  # type: ignore[misc]

        # Identificar por API key + IP
        api_key = request.headers.get("X-API-Key", "")
        client_ip = request.client.host if request.client else "unknown"
        key = f"{api_key}:{client_ip}"

        # Limpiar timestamps expirados
        now = time.monotonic()
        cutoff = now - 60.0
        self._requests[key] = [
            t for t in self._requests[key] if t > cutoff
        ]

        # Verificar límite
        if len(self._requests[key]) >= RATE_LIMIT_POR_MINUTO:
            error = ErrorEnvelope(
                error=ErrorDetail(
                    codigo="DEMASIADAS_SOLICITUDES",
                    mensaje="Se excedieron 30 análisis en un minuto.",
                )
            )
            return JSONResponse(
                status_code=429,
                content=error.model_dump(),
            )

        # Registrar y continuar
        self._requests[key].append(now)
        return await call_next(request)  # type: ignore[misc]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade cabeceras de seguridad (FR-003)."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response = await call_next(request)  # type: ignore[misc]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response
