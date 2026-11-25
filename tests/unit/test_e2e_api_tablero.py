"""Tests E2E del tablero: métricas, jobs de Gmail e integraciones (spec 012).

Parte 2 de los escenarios que test_e2e_api.py no alcanza:
- GET /api/metrics/summary — rangos 7d/30d/90d
- GET  /api/jobs/gmail     — estado del poller
- POST /api/jobs/gmail/run — forzar ciclo
- GET  /api/integraciones  — sin claves en la respuesta

El CRUD/exportación vive en test_e2e_api_scenarios.py y los casos de
borde en test_e2e_api_borde.py (límite de 500 líneas por archivo).
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble

from test_e2e_api import (
    _crear_cliente,
    _headers,
    _limpiar_env,
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
# GET /api/metrics/summary
# ---------------------------------------------------------------------------


class TestMetricsSummary:
    """Métricas del tablero."""

    def test_metricas_7d_retorna_200(self) -> None:
        """GET /metrics/summary?rango=7d → 200."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/metrics/summary?rango=7d", headers=_headers())
            assert resp.status_code == 200
        finally:
            _limpiar_env()

    def test_metricas_30d_retorna_200(self) -> None:
        """GET /metrics/summary?rango=30d → 200."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/metrics/summary?rango=30d", headers=_headers())
            assert resp.status_code == 200
        finally:
            _limpiar_env()

    def test_metricas_90d_retorna_200(self) -> None:
        """GET /metrics/summary?rango=90d → 200."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/metrics/summary?rango=90d", headers=_headers())
            assert resp.status_code == 200
        finally:
            _limpiar_env()

    def test_metricas_estructura_correcta(self) -> None:
        """La respuesta de métricas tiene los campos esperados."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/metrics/summary?rango=7d", headers=_headers())
            data = resp.json()
            campos = ("rango", "total", "por_veredicto", "por_dia")
            for campo in campos:
                assert campo in data, f"Falta campo: {campo}"
        finally:
            _limpiar_env()

    def test_metricas_rango_invalido_retorna_422(self) -> None:
        """Rango desconocido → 422."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/metrics/summary?rango=99d", headers=_headers())
            assert resp.status_code == 422
        finally:
            _limpiar_env()

    def test_metricas_sin_auth_retorna_401(self) -> None:
        """GET /metrics/summary sin key → 401."""
        client = _crear_cliente()
        try:
            resp = client.get(
                "/api/metrics/summary?rango=7d",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# GET/POST /api/jobs/gmail
# ---------------------------------------------------------------------------


class TestJobsGmail:
    """Endpoints de gestión del poller Gmail."""

    def test_get_jobs_gmail_retorna_200(self) -> None:
        """GET /jobs/gmail → 200 con estructura de estado."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/jobs/gmail", headers=_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert "pendientes" in data
            assert "fallidos" in data
        finally:
            _limpiar_env()

    def test_post_jobs_gmail_run_retorna_200(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /jobs/gmail/run → 200 con timestamp.

        La tarea de background ejecuta el ciclo real de Gmail (OAuth + red),
        así que el test la sustituye por un no-op y solo valida la respuesta
        del endpoint.
        """
        monkeypatch.setattr("src.api.routers.jobs._run_ciclo_gmail", lambda: None)
        client = _crear_cliente()
        try:
            resp = client.post("/api/jobs/gmail/run", headers=_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert "ultimo_ciclo" in data
        finally:
            _limpiar_env()

    def test_jobs_gmail_sin_auth_retorna_401(self) -> None:
        """GET /jobs/gmail sin key → 401."""
        client = _crear_cliente()
        try:
            resp = client.get(
                "/api/jobs/gmail",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# GET /api/integraciones
# ---------------------------------------------------------------------------


class TestIntegraciones:
    """Estado de integraciones externas."""

    def test_integraciones_retorna_200(self) -> None:
        """GET /integraciones → 200."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/integraciones", headers=_headers())
            assert resp.status_code == 200
        finally:
            _limpiar_env()

    def test_integraciones_estructura(self) -> None:
        """La respuesta tiene los campos mongo/virustotal/modelo/gmail."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/integraciones", headers=_headers())
            data = resp.json()
            for clave in ("mongo", "virustotal", "modelo", "gmail"):
                assert clave in data, f"Falta integración: {clave}"
        finally:
            _limpiar_env()

    def test_integraciones_no_revela_claves(self) -> None:
        """AC-API-06: la respuesta NO contiene valores de API keys."""
        os.environ["API_KEY"] = "test-scenarios-key"
        os.environ["VT_API_KEY"] = "vt-secret-key-12345"
        os.environ["GOOGLE_API_KEY"] = "google-secret-key-67890"
        os.environ["LLM_PROVEEDOR"] = "simulado"
        try:
            app = create_app()
            app.state.repo = RepositorioAnalisisDoble()
            app.state.cache_vt = CacheVTDoble()
            client = TestClient(app)
            resp = client.get(
                "/api/integraciones",
                headers={"X-API-Key": "test-scenarios-key"},
            )
            resp_text = resp.text
            assert "vt-secret-key-12345" not in resp_text
            assert "google-secret-key-67890" not in resp_text
        finally:
            os.environ.pop("API_KEY", None)
            os.environ.pop("VT_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("LLM_PROVEEDOR", None)

    def test_integraciones_sin_auth_retorna_401(self) -> None:
        """GET /integraciones sin key → 401."""
        client = _crear_cliente()
        try:
            resp = client.get(
                "/api/integraciones",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
        finally:
            _limpiar_env()
