"""AC-API-04: CSV exportación con BOM, escape y límite."""

from __future__ import annotations

import pytest

import os

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


@pytest.mark.ac("AC-API-04")
def test_export_csv_endpoint() -> None:
    """GET /analyses/export.csv → 200 con text/csv."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    r = c.get("/api/analyses/export.csv", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    # BOM UTF-8
    assert r.text.startswith("\ufeff")
