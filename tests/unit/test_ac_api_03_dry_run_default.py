"""AC-API-03: dry_run está activo por defecto y la respuesta lo refleja."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


@pytest.fixture(autouse=True)
def _aislar_entorno_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla de MongoDB real (auditoría AUD-01).

    `test_dry_run_explicit_false` ejecuta el acciones real vía API y, sin
    este delenv, escriía `api_<ts>` en la BD de producción (idempotencia).
    """
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)


def _client() -> TestClient:
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    return TestClient(app)


@pytest.mark.ac("AC-API-03")
def test_dry_run_default_true() -> None:
    """POST /analyses sin dry_run explícito → simulada=true."""
    c = _client()
    r = c.post(
        "/api/analyses",
        json={"modo": "pegar", "subject": "Test", "text": "Hello"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["accion"]["simulada"] is True


@pytest.mark.ac("AC-API-03")
def test_dry_run_explicit_false() -> None:
    """POST /analyses con dry_run=false → simulada=false."""
    c = _client()
    r = c.post(
        "/api/analyses",
        json={"modo": "pegar", "dry_run": False, "subject": "Test", "text": "Hello"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["accion"]["simulada"] is False
