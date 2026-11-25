"""FastAPI application factory (spec 012, M14).

create_app() → FastAPI con routers, middleware, exception handlers.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import API_PREFIX, get_cors_origins
from .errors import APIError, ErrorDetail, ErrorEnvelope
from .middleware import RateLimiter, SecurityHeadersMiddleware
from .persistence_repos import CacheVTDoble, RepositorioAnalisisDoble
from .routers import analisis, integraciones, jobs, metricas, muestras, salud


def create_app() -> FastAPI:
    """Crea la aplicación FastAPI con todos los routers y middleware."""
    # Auditoría 2026-11-20: cargar .env de la raíz en el arranque. Antes la
    # API dependía del efecto secundario del import de agent.py (load_dotenv
    # en módulo), lo que hacía frágil el orden de imports.
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

    app = FastAPI(
        title="PhishGuard-AI API",
        version="1.0.0",
        description="API REST de PhishGuard-AI para el frontend (spec 012).",
    )

    # --- State (repositorios simulables en tests) ---
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()

    # --- Middleware ---
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimiter)

    cors_origins = get_cors_origins()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    # --- Exception handlers ---
    @app.exception_handler(APIError)
    async def api_error_handler(
        request: Request, exc: APIError
    ) -> JSONResponse:
        error = ErrorEnvelope(
            error=ErrorDetail(
                codigo=exc.codigo,
                mensaje=exc.mensaje,
                detalles=exc.detalles,
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """422 → VALIDACION con envelope uniforme (FR-002)."""
        error = ErrorEnvelope(
            error=ErrorDetail(
                codigo="VALIDACION",
                mensaje="La solicitud no pasó la validación.",
                detalles=list(exc.errors()),
            )
        )
        return JSONResponse(
            status_code=422,
            content=error.model_dump(),
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """500 → ERROR_INTERNO con envelope uniforme (FR-002)."""
        error = ErrorEnvelope(
            error=ErrorDetail(
                codigo="ERROR_INTERNO",
                mensaje="Error interno del servidor.",
            )
        )
        return JSONResponse(
            status_code=500,
            content=error.model_dump(),
        )

    # --- Routers bajo /api ---
    app.include_router(salud.router, prefix=API_PREFIX)
    # Alias de salud en la raíz (sin /api) para probes externos: Render,
    # monitores y load balancers suelen golpear /health directamente.
    app.include_router(salud.router, include_in_schema=False)
    app.include_router(integraciones.router, prefix=API_PREFIX)
    app.include_router(muestras.router, prefix=API_PREFIX)
    app.include_router(analisis.router, prefix=API_PREFIX)
    app.include_router(metricas.router, prefix=API_PREFIX)
    app.include_router(jobs.router, prefix=API_PREFIX)

    # --- Raíz: evita 404 en el probe HEAD/GET / de Render ---
    @app.get("/", include_in_schema=False)
    async def raiz() -> dict[str, str]:
        """Punto de entrada del servicio (sin autenticación)."""
        return {"servicio": "phishguard-ai-api", "salud": "/api/health"}

    return app
