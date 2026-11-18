"""AC-API-07: sin X-API-Key válida, todo endpoint salvo health devuelve 401."""

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


@pytest.mark.ac("AC-API-07")
def test_health_sin_key_ok() -> None:
    """GET /api/health sin key → 200 (exento)."""
    c = _client()
    r = c.get("/api/health")
    assert r.status_code == 200


@pytest.mark.ac("AC-API-07")
def test_integraciones_sin_key_401() -> None:
    """GET /api/integraciones sin key → 401."""
    c = _client()
    r = c.get("/api/integraciones")
    assert r.status_code == 401


@pytest.mark.ac("AC-API-07")
def test_analyses_sin_key_401() -> None:
    """GET /api/analyses sin key → 401."""
    c = _client()
    r = c.get("/api/analyses")
    assert r.status_code == 401


@pytest.mark.ac("AC-API-07")
def test_metrics_sin_key_401() -> None:
    """GET /api/metrics/summary sin key → 401."""
    c = _client()
    r = c.get("/api/metrics/summary", params={"rango": "7d"})
    assert r.status_code == 401


@pytest.mark.ac("AC-API-07")
def test_jobs_sin_key_401() -> None:
    """GET /api/jobs/gmail sin key → 401."""
    c = _client()
    r = c.get("/api/jobs/gmail")
    assert r.status_code == 401


@pytest.mark.ac("AC-API-07")
def test_key_invalida_401() -> None:
    """Key incorrecta → 401."""
    c = _client()
    r = c.get("/api/analyses", headers={"X-API-Key": "wrong-key"})
    assert r.status_code == 401
