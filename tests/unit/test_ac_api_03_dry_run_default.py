"""AC-API-03: dry_run está activo por defecto y la respuesta lo refleja."""

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
