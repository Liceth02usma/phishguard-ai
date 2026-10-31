"""AC-API-01: cada endpoint cumple la forma de respuesta y los códigos de RF1 y RF2."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


def _client() -> TestClient:
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    return TestClient(app)


@pytest.mark.ac("AC-API-01")
def test_health_200() -> None:
    """GET /api/health → 200 con {estado: ok}."""
    c = _client()
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


@pytest.mark.ac("AC-API-01")
def test_integraciones_200() -> None:
    """GET /api/integraciones → 200 con estructura esperada."""
    c = _client()
    r = c.get("/api/integraciones", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    data = r.json()
    assert "mongo" in data
    assert "virustotal" in data
    assert "modelo" in data
    assert "gmail" in data


@pytest.mark.ac("AC-API-01")
def test_samples_200() -> None:
    """GET /api/samples → 200 con lista."""
    c = _client()
    r = c.get("/api/samples", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.ac("AC-API-01")
def test_list_analyses_200() -> None:
    """GET /api/analyses → 200 con paginación."""
    c = _client()
    r = c.get("/api/analyses", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "pagina" in data
    assert "total" in data


@pytest.mark.ac("AC-API-01")
def test_metrics_summary_200() -> None:
    """GET /api/metrics/summary?rango=7d → 200."""
    c = _client()
    r = c.get(
        "/api/metrics/summary", params={"rango": "7d"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "por_veredicto" in data


@pytest.mark.ac("AC-API-01")
def test_jobs_gmail_200() -> None:
    """GET /api/jobs/gmail → 200."""
    c = _client()
    r = c.get("/api/jobs/gmail", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200


@pytest.mark.ac("AC-API-01")
def test_error_envelope_form() -> None:
    """Errores tienen forma {error: {codigo, mensaje, detalles}}."""
    c = _client()
    r = c.get("/api/integraciones")  # sin API key
    assert r.status_code == 401
    data = r.json()
    assert "error" in data
    assert "codigo" in data["error"]
    assert "mensaje" in data["error"]
