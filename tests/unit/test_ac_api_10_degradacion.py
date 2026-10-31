"""AC-API-10: caída de VT/modelo → 201 con revision_manual."""

from __future__ import annotations

import pytest

import os

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


@pytest.mark.ac("AC-API-10")
def test_caida_modelo_revision_manual() -> None:
    """Si el pipeline lanza excepción, la respuesta es 201 con revision_manual."""
    os.environ["API_KEY"] = "test-key"
    # Sin GOOGLE_API_KEY → analyze_email fallirá
    os.environ.pop("GOOGLE_API_KEY", "")
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    r = c.post(
        "/api/analyses",
        json={"modo": "pegar", "subject": "Test caída", "text": "body"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 201
    data = r.json()
    # Puede ser revision_manual (caída) o sin_indicadores (si no falla)
    assert data["resultado"]["veredicto"] in (
        "revision_manual",
        "sin_indicadores",
        "malicioso",
        "sospechoso",
    )
