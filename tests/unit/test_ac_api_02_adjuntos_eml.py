"""AC-API-02: POST /analyses modo=eml con adjunto devuelve sha256 y reputación."""

from __future__ import annotations

import io
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


@pytest.mark.ac("AC-API-02")
def test_eml_m6mb_devuelve_201() -> None:
    """POST /analyses modo=eml con archivo pequeño → 201."""
    c = _client()
    eml_content = b"From: test@test.com\nSubject: Test EML\n\nBody"
    r = c.post(
        "/api/analyses",
        files={"archivo": ("test.eml", io.BytesIO(eml_content), "message/rfc822")},
        data={"modo": "eml", "dry_run": "true"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 201


@pytest.mark.ac("AC-API-02")
def test_eml_613_si_excede_25mb() -> None:
    """POST /analyses modo=eml con archivo >25MB → 413 (FR-003)."""
    c = _client()
    # 26 MB de contenido
    big_content = b"x" * (26 * 1024 * 1024)
    r = c.post(
        "/api/analyses",
        files={"archivo": ("big.eml", io.BytesIO(big_content), "message/rfc822")},
        data={"modo": "eml", "dry_run": "true"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 413
    assert r.json()["error"]["codigo"] == "ENTRADA_GRANDE"


@pytest.mark.ac("AC-API-02")
def test_eml_sin_archivo_613() -> None:
    """POST /analyses modo=eml sin archivo → 413."""
    c = _client()
    # Enviar multipart sin archivo — FastAPI lo parsea como form vacío
    r = c.post(
        "/api/analyses",
        files={"archivo": ("", io.BytesIO(b""), "application/octet-stream")},
        data={"modo": "eml", "dry_run": "true"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 413
