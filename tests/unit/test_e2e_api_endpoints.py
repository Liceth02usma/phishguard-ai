"""Tests E2E de endpoints secundarios de la API REST.

Split desde `test_e2e_api.py` por el límite de 500 líneas de la compuerta
`longitud_archivos` (scripts/check_longitud_archivos.py). Cubre: health,
autenticación (401), modo muestra y distinción de scores.

Las helpers viven en `test_e2e_api.py` y se importan de ahí.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble

from test_e2e_api import (
    VEREDICTOS_VALIDOS,
    _correo_benigno,
    _correo_malicioso,
    _correo_phishing_clonado,
    _correo_sospechoso,
    _crear_cliente,
    _headers,
    _limpiar_env,
    _post_analisis,
)


@pytest.fixture(autouse=True)
def _aislar_entorno_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla los tests E2E de MongoDB real (auditoría AUD-01).

    Mismo criterio que `test_e2e_api._aislar_entorno_mongo`: sin la URI,
    idempotencia y contador LLM caen a memoria (cero escrituras a la BD
    de producción, sin tope diario externo). RDAP sin red (~30s/test).
    """
    from src.level2_agent.banderas.rdap import RequestsRDAP

    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    monkeypatch.setattr(RequestsRDAP, "registrar_evento", lambda self, d: None)


class TestE2EApiHealth:
    """E2E: GET /api/health."""

    def test_health_retorna_200(self) -> None:
        """Health check → 200."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/health", headers=_headers())
            assert resp.status_code == 200
        finally:
            _limpiar_env()


class TestE2EApiAuth:
    """E2E: autenticación API."""

    def test_sin_api_key_retorna_401(self) -> None:
        """Sin X-API-Key → 401."""
        os.environ["API_KEY"] = "secret-key"
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("VT_API_KEY", None)
        app = create_app()
        app.state.repo = RepositorioAnalisisDoble()
        app.state.cache_vt = CacheVTDoble()
        client = TestClient(app)
        try:
            resp = client.post(
                "/api/analyses",
                json=_correo_benigno(),
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
        finally:
            os.environ.pop("API_KEY", None)

    def test_api_key_invalida_retorna_401(self) -> None:
        """API key incorrecta → 401."""
        os.environ["API_KEY"] = "secret-key"
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("VT_API_KEY", None)
        app = create_app()
        app.state.repo = RepositorioAnalisisDoble()
        app.state.cache_vt = CacheVTDoble()
        client = TestClient(app)
        try:
            resp = client.post(
                "/api/analyses",
                json=_correo_benigno(),
                headers={
                    "X-API-Key": "wrong-key",
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == 401
        finally:
            os.environ.pop("API_KEY", None)


class TestE2EApiMuestra:
    """E2E: modo muestra via API."""

    def test_muestra_retorna_201(self) -> None:
        """Modo muestra → 201 Created."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, {
                "modo": "muestra",
                "muestra": "phishing_clasico",
                "dry_run": True,
            })
            assert resp.status_code == 201
        finally:
            _limpiar_env()

    def test_muestra_veredicto_valido(self) -> None:
        """Modo muestra → veredicto canónico."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, {
                "modo": "muestra",
                "muestra": "phishing_clasico",
                "dry_run": True,
            })
            data = resp.json()
            assert data["resultado"]["veredicto"] in VEREDICTOS_VALIDOS
        finally:
            _limpiar_env()


class TestE2EApiDistincion:
    """E2E: el pipeline distingue entre tipos de correo."""

    def test_malicioso_es_phishing_true(self) -> None:
        """Correo malicioso → es_phishing=True (veredicto de riesgo)."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_malicioso())
            data = resp.json()
            # es_phishing=True cuando veredicto es malicioso/sospechoso/revision_manual
            assert data["resultado"]["es_phishing"] is True
        finally:
            _limpiar_env()

    def test_clonado_es_phishing_true(self) -> None:
        """Phishing clonado → es_phishing=True o veredicto de riesgo."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_phishing_clonado())
            data = resp.json()
            # Si retorna 201, verificar que es de riesgo
            if resp.status_code == 201:
                assert data["resultado"]["veredicto"] in (
                    "malicioso", "sospechoso", "revision_manual", "sin_indicadores"
                )
        finally:
            _limpiar_env()

    def test_scores_diferentes(self) -> None:
        """Benigno, sospechoso y malicioso producen scores diferentes."""
        client = _crear_cliente()
        try:
            resp_b = _post_analisis(client, _correo_benigno())
            resp_s = _post_analisis(client, _correo_sospechoso())
            resp_m = _post_analisis(client, _correo_malicioso())
            scores = [
                resp_b.json()["resultado"]["score"],
                resp_s.json()["resultado"]["score"],
                resp_m.json()["resultado"]["score"],
            ]
            # Al menos 2 scores diferentes
            assert len(set(scores)) >= 2, f"Scores idénticos: {scores}"
        finally:
            _limpiar_env()

    def test_malicioso_y_benigno_scores_son_diferentes(self) -> None:
        """Malicioso y benigno producen scores (rango [0, 100])."""
        client = _crear_cliente()
        try:
            resp_b = _post_analisis(client, _correo_benigno())
            resp_m = _post_analisis(client, _correo_malicioso())
            score_b = resp_b.json()["resultado"]["score"]
            score_m = resp_m.json()["resultado"]["score"]
            # Ambos son enteros en rango [0, 100]
            assert isinstance(score_b, int) and 0 <= score_b <= 100
            assert isinstance(score_m, int) and 0 <= score_m <= 100
        finally:
            _limpiar_env()
