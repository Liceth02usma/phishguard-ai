"""AC-API-05: métricas con rango 7d/30d/90d."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


def _client() -> TestClient:
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    return TestClient(app)


def test_metrics_rango_7d() -> None:
    """GET /metrics/summary?rango=7d → 200."""
    c = _client()
    r = c.get(
        "/api/metrics/summary",
        params={"rango": "7d"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    assert r.json()["rango"] == "7d"


def test_metrics_rango_30d() -> None:
    """GET /metrics/summary?rango=30d → 200."""
    c = _client()
    r = c.get(
        "/api/metrics/summary",
        params={"rango": "30d"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    assert r.json()["rango"] == "30d"


def test_metrics_rango_90d() -> None:
    """GET /metrics/summary?rango=90d → 200."""
    c = _client()
    r = c.get(
        "/api/metrics/summary",
        params={"rango": "90d"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    assert r.json()["rango"] == "90d"


def test_metrics_rango_invalido() -> None:
    """GET /metrics/summary?rango=1y → 422."""
    c = _client()
    r = c.get(
        "/api/metrics/summary",
        params={"rango": "1y"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 422
