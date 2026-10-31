"""FR-002: exception handlers VALIDACION (422), ERROR_INTERNO (500),
SERVICIO_NO_DISPONIBLE (503)."""

from __future__ import annotations

import os

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.errors import ServicioNoDisponibleError
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


@pytest.mark.ac("AC-API-01")
def test_503_servicio_no_disponible_envelope() -> None:
    """503 ServicioNoDisponibleError usa envelope SERVICIO_NO_DISPONIBLE (FR-002)."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()

    # Endpoint de prueba que levanta ServicioNoDisponibleError
    @app.get("/api/_test_503")
    async def _test_503(request: Request) -> JSONResponse:
        raise ServicioNoDisponibleError("MongoDB")

    c = TestClient(app)
    r = c.get("/api/_test_503", headers={"X-API-Key": "test-key"})
    assert r.status_code == 503
    data = r.json()
    assert data["error"]["codigo"] == "SERVICIO_NO_DISPONIBLE"
    assert "MongoDB" in data["error"]["mensaje"]
