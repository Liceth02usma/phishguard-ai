"""FR-002: exception handlers para VALIDACION (422), ERROR_INTERNO (500) y SERVICIO_NO_DISPONIBLE (503)."""

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
def test_422_validacion_envelope() -> None:
    """422 de validacion usa envelope VALIDACION (FR-002)."""
    c = _client()
    # Enviar query param invalido (pagina=0 viola ge=1)
    r = c.get(
        "/api/analyses",
        params={"pagina": 0},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 422
    data = r.json()
    assert data["error"]["codigo"] == "VALIDACION"
    assert "mensaje" in data["error"]
