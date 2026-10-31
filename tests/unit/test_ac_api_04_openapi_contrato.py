"""AC-API-04: la documentación OpenAPI refleja el contrato real (prueba de contrato)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.mark.ac("AC-API-04")
def test_openapi_json_accessible() -> None:
    """GET /openapi.json → 200 con schema válido."""
    app = create_app()
    c = TestClient(app)
    r = c.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "/api/health" in schema["paths"]


@pytest.mark.ac("AC-API-04")
def test_openapi_contiene_endpoints_esperados() -> None:
    """El schema OpenAPI contiene todos los endpoints de FR-001."""
    app = create_app()
    c = TestClient(app)
    schema = c.get("/openapi.json").json()
    paths = schema["paths"]

    expected = [
        "/api/health",
        "/api/integraciones",
        "/api/samples",
        "/api/analyses",
        "/api/metrics/summary",
        "/api/jobs/gmail",
    ]
    for ep in expected:
        assert ep in paths, f"Endpoint {ep} no encontrado en OpenAPI"


@pytest.mark.ac("AC-API-04")
def test_openapi_contiene_schemas_de_respuesta() -> None:
    """El schema OpenAPI define los componentes de respuesta."""
    app = create_app()
    c = TestClient(app)
    schema = c.get("/openapi.json").json()
    components = schema.get("components", {}).get("schemas", {})

    # Verificar que existen los schemas principales
    assert "AnalisisResponse" in components
    assert "MetricasResponse" in components
