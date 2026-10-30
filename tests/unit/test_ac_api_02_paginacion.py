"""AC-API-02: paginación con limite máximo 50 y default 50."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


def test_paginacion_default_limite_50() -> None:
    """GET /analyses sin limite → limite=50."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    r = c.get("/api/analyses", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    data = r.json()
    assert data["limite"] == 50


def test_paginacion_limite_max_50() -> None:
    """limite=51 → 422 (excede máximo)."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    r = c.get(
        "/api/analyses",
        params={"limite": 51},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 422


def test_paginacion_pagina_1() -> None:
    """pagina=0 → 422 (mínimo 1)."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    r = c.get(
        "/api/analyses",
        params={"pagina": 0},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 422
