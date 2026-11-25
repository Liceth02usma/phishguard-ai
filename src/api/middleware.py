"""Middleware de la API (spec 012, FR-003).

RateLimiter: 30 análisis/min por clave e IP.
SecurityHeadersMiddleware: cabeceras de seguridad.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import MutableMapping
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import RATE_LIMIT_POR_MINUTO
from .errors import ErrorDetail, ErrorEnvelope


class RateLimiter:
    """Rate limiter in-memory: 30 análisis/min por API key e IP.

    Solo aplica a POST /api/analyses (AC-API-09).

    Middleware ASGI puro (sin BaseHTTPMiddleware): evita el task group
    interno de call_next, que interfiere con el trazado de coverage en
    los handlers async durante la suspensión de corrutinas.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        # Solo limitar POST /api/analyses
        if request.method != "POST" or request.url.path != "/api/analyses":
            await self.app(scope, receive, send)
            return

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
            response = JSONResponse(
                status_code=429,
                content=error.model_dump(),
            )
            await response(scope, receive, send)
            return

        # Registrar y continuar
        self._requests[key].append(now)
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Añade cabeceras de seguridad (FR-003).

    Middleware ASGI puro: inyecta las cabeceras en el mensaje
    http.response.start sin task groups intermedios.
    """

    _HEADERS = (
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"cache-control", b"no-store"),
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._HEADERS)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
