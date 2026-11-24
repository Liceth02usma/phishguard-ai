"""AC-API-09: rate limit de 30 análisis/min por clave e IP."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


@pytest.mark.ac("AC-API-09")
def test_rate_limit_429_despues_de_30() -> None:
    """30+ POST /analyses en un minuto → 429."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    headers = {"X-API-Key": "test-key"}
    body = {"modo": "pegar", "subject": "Test", "text": "x"}

    # Parchear pipeline para que sea instantáneo: cada llamada tarda ~2s y
    # con 30 requests el primer timestamp saldría de la ventana de 60s antes
    # del request 31. AC-API-10 captura el RuntimeError → 201 de igual forma.
    with patch(
        "src.level2_agent.agent.analyze_email",
        side_effect=RuntimeError("mock-rate-limit"),
    ):
        # 30 requests → todas 201 (graceful degradation AC-API-10)
        for _ in range(30):
            r = c.post("/api/analyses", json=body, headers=headers)
            assert r.status_code == 201, f"Expected 201, got {r.status_code}"

        # Request 31 → 429 (el middleware intercepta antes del handler)
        r = c.post("/api/analyses", json=body, headers=headers)

    assert r.status_code == 429
    data = r.json()
    assert data["error"]["codigo"] == "DEMASIADAS_SOLICITUDES"


@pytest.mark.ac("AC-API-09")
def test_rate_limit_no_aplica_a_get() -> None:
    """GET /analyses no está sujeto a rate limit."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    headers = {"X-API-Key": "test-key"}

    # 35 GETs → todas 200
    for _ in range(35):
        r = c.get("/api/analyses", headers=headers)
        assert r.status_code == 200
