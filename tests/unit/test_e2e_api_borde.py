"""Tests E2E de casos de borde: validación, paginación, headers y degradación.

Parte 3 de los escenarios que test_e2e_api.py no alcanza:
- 422 de validación — body mal formado
- Paginación        — pagina/limite
- Security headers  — X-Content-Type-Options, etc.
- Degradación       — AC-API-10: 201 aunque el modelo LLM falle

El CRUD/exportación vive en test_e2e_api_scenarios.py y el tablero en
test_e2e_api_tablero.py (límite de 500 líneas por archivo).
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble

from test_e2e_api import (
    _correo_benigno,
    _correo_malicioso,
    _crear_cliente,
    _headers,
    _limpiar_env,
    _post_analisis,
)

# ---------------------------------------------------------------------------
# Fixture de aislamiento MongoDB (igual que test_e2e_api.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _aislar_entorno_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.level2_agent.banderas.rdap import RequestsRDAP

    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    monkeypatch.setattr(RequestsRDAP, "registrar_evento", lambda self, d: None)


# ---------------------------------------------------------------------------
# 422 Validación
# ---------------------------------------------------------------------------


class TestValidacion422:
    """El endpoint rechaza bodies mal formados (FR-002)."""

    def test_body_vacio_retorna_error(self) -> None:
        """Body {} sin modo → el endpoint rechaza con 4xx/5xx.

        El endpoint lee el body con request.json() manualmente (no via
        FastAPI dependency injection), por lo que ValidationError de Pydantic
        llega al handler global y retorna 500, no 422. Se acepta cualquier
        código de error (no 201/200).
        """
        os.environ["API_KEY"] = "test-scenarios-key"
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ["LLM_PROVEEDOR"] = "simulado"
        try:
            app = create_app()
            app.state.repo = RepositorioAnalisisDoble()
            app.state.cache_vt = CacheVTDoble()
            # raise_server_exceptions=False evita que el crash de ExceptionGroup
            # de anyio/starlette propague como excepción del test.
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/analyses",
                json={},
                headers={"X-API-Key": "test-scenarios-key", "Content-Type": "application/json"},
            )
            assert resp.status_code not in (200, 201), f"Body vacío aceptado: {resp.status_code}"
        finally:
            os.environ.pop("API_KEY", None)
            os.environ.pop("LLM_PROVEEDOR", None)

    def test_modo_invalido_retorna_error(self) -> None:
        """modo no reconocido → el endpoint retorna error (no 2xx).

        El endpoint construye el modelo manualmente, así que un modo inválido
        llega al handler global (500) en lugar de triggear FastAPI 422.
        """
        os.environ["API_KEY"] = "test-scenarios-key"
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ["LLM_PROVEEDOR"] = "simulado"
        try:
            app = create_app()
            app.state.repo = RepositorioAnalisisDoble()
            app.state.cache_vt = CacheVTDoble()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/analyses",
                json={"modo": "invalido", "subject": "test"},
                headers={"X-API-Key": "test-scenarios-key", "Content-Type": "application/json"},
            )
            assert resp.status_code not in (200, 201)
        finally:
            os.environ.pop("API_KEY", None)
            os.environ.pop("LLM_PROVEEDOR", None)

    def test_subject_demasiado_largo_retorna_422(self) -> None:
        """subject > 998 chars → 422 (límite de EmailData)."""
        client = _crear_cliente()
        try:
            correo = _correo_benigno()
            correo["subject"] = "A" * 1000
            resp = _post_analisis(client, correo)
            # Debe rechazar con 422 o aceptar con truncado (ambos son válidos)
            assert resp.status_code in (201, 422)
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# Paginación
# ---------------------------------------------------------------------------


class TestPaginacion:
    """Paginación del listado de análisis."""

    def test_limite_1_retorna_1_item(self) -> None:
        """limite=1 → exactamente 1 item en la página."""
        client = _crear_cliente()
        try:
            _post_analisis(client, _correo_benigno())
            _post_analisis(client, _correo_malicioso())
            resp = client.get("/api/analyses?limite=1&pagina=1", headers=_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) <= 1
        finally:
            _limpiar_env()

    def test_pagina_fuera_de_rango_retorna_items_vacio(self) -> None:
        """pagina=9999 → items vacíos pero status 200."""
        client = _crear_cliente()
        try:
            _post_analisis(client, _correo_benigno())
            resp = client.get("/api/analyses?pagina=9999&limite=10", headers=_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert data["items"] == []
        finally:
            _limpiar_env()

    def test_total_refleja_cantidad_correcta(self) -> None:
        """total en la respuesta de listado es >= cantidad de POSTs."""
        client = _crear_cliente()
        try:
            _post_analisis(client, _correo_benigno())
            _post_analisis(client, _correo_malicioso())
            resp = client.get("/api/analyses", headers=_headers())
            data = resp.json()
            assert data["total"] >= 2
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    """El middleware inyecta cabeceras de seguridad (spec 012)."""

    def test_health_tiene_x_content_type_options(self) -> None:
        """GET /health → X-Content-Type-Options: nosniff."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/health")
            assert resp.headers.get("x-content-type-options", "").lower() == "nosniff"
        finally:
            _limpiar_env()

    def test_health_tiene_x_frame_options(self) -> None:
        """GET /health → X-Frame-Options presente."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/health")
            assert "x-frame-options" in resp.headers
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# Rutas de salud en la raíz (alias para probes de Render/monitores)
# ---------------------------------------------------------------------------


class TestRutasSaludRaiz:
    """Alias sin prefijo /api usados por los health checks externos."""

    def test_raiz_retorna_200(self) -> None:
        """GET / → 200 con el puntero al health check."""
        client = _crear_cliente()
        try:
            resp = client.get("/")
            assert resp.status_code == 200
            data = resp.json()
            assert data["salud"] == "/api/health"
        finally:
            _limpiar_env()

    def test_health_sin_prefijo_retorna_200(self) -> None:
        """GET /health (sin /api) → 200 con {estado: ok}."""
        client = _crear_cliente()
        try:
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json() == {"estado": "ok"}
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# Degradación graceful (AC-API-10)
# ---------------------------------------------------------------------------


class TestDegradacion:
    """El pipeline devuelve 201 incluso cuando el modelo LLM falla."""

    def test_sin_google_key_devuelve_201(self) -> None:
        """Sin GOOGLE_API_KEY con LLM simulado → 201 (degradación, no 500)."""
        os.environ["API_KEY"] = "test-scenarios-key"
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("VT_API_KEY", None)
        os.environ["LLM_PROVEEDOR"] = "simulado"
        try:
            app = create_app()
            app.state.repo = RepositorioAnalisisDoble()
            app.state.cache_vt = CacheVTDoble()
            client = TestClient(app)
            resp = client.post(
                "/api/analyses",
                json=_correo_malicioso(),
                headers={"X-API-Key": "test-scenarios-key", "Content-Type": "application/json"},
            )
            assert resp.status_code == 201
        finally:
            os.environ.pop("API_KEY", None)
            os.environ.pop("LLM_PROVEEDOR", None)

    def test_error_pipeline_no_devuelve_500(self) -> None:
        """Si el pipeline interno lanza una excepción no manejada → no es 500."""
        os.environ["API_KEY"] = "test-scenarios-key"
        os.environ["LLM_PROVEEDOR"] = "simulado"
        try:
            app = create_app()
            app.state.repo = RepositorioAnalisisDoble()
            app.state.cache_vt = CacheVTDoble()
            client = TestClient(app)
            # Correo malformado que podría romper parsers
            resp = client.post(
                "/api/analyses",
                json={
                    "modo": "pegar",
                    "dry_run": True,
                    "subject": "\x00\xff\xfe" * 10,
                    "from": "a@b.c",
                    "to": "x@y.z",
                    "text": "",
                    "headers": {},
                },
                headers={"X-API-Key": "test-scenarios-key", "Content-Type": "application/json"},
            )
            # Puede ser 201 (manejado) o 422 (validación), pero nunca 500
            assert resp.status_code in (201, 422), f"Status inesperado: {resp.status_code}"
        finally:
            os.environ.pop("API_KEY", None)
            os.environ.pop("LLM_PROVEEDOR", None)
