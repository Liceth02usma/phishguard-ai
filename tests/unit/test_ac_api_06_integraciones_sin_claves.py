"""AC-API-06: GET /integraciones no revela claves ni URLs internas."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


@pytest.mark.ac("AC-API-06")
def test_integraciones_sin_claves() -> None:
    """La respuesta no contiene claves, URIs ni tokens."""
    os.environ["API_KEY"] = "test-key"
    os.environ["MONGODB_ATLAS_CLUSTER_URI"] = "mongodb+srv://user:secret@cluster.mongodb.net/"
    os.environ["VT_API_KEY"] = "vt-secret-key-12345"
    os.environ["GOOGLE_API_KEY"] = "google-secret-key"
    try:
        app = create_app()
        app.state.repo = RepositorioAnalisisDoble()
        app.state.cache_vt = CacheVTDoble()
        c = TestClient(app)
        r = c.get("/api/integraciones", headers={"X-API-Key": "test-key"})
        assert r.status_code == 200
        body = r.text
        # Ningún secreto aparece en la respuesta
        assert "secret" not in body
        assert "vt-secret-key" not in body
        assert "google-secret" not in body
        assert "mongodb+srv" not in body
    finally:
        os.environ.pop("MONGODB_ATLAS_CLUSTER_URI", "")
        os.environ.pop("VT_API_KEY", "")
        os.environ.pop("GOOGLE_API_KEY", "")
