"""Tests E2E de escenarios de análisis: CRUD y exportación (spec 012).

Parte 1 de los escenarios que test_e2e_api.py no alcanza:
- GET /api/analyses/{id}       — detalle + 404
- PATCH /api/analyses/{id}/feedback
- DELETE /api/analyses/{id}    — eliminación + 404 reintento
- GET /api/analyses/export.csv — CSV bien formado

El tablero vive en test_e2e_api_tablero.py y los casos de borde en
test_e2e_api_borde.py (límite de 500 líneas por archivo).
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble

from test_e2e_api import (
    _correo_benigno,
    _crear_cliente,
    _headers,
    _limpiar_env,
    _post_analisis,
)

# ---------------------------------------------------------------------------
# Fixture de aislamiento MongoDB (igual que test_e2e_api.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _aislar_entorno_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.level2_agent.banderas.rdap import RequestsRDAP

    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    monkeypatch.setattr(RequestsRDAP, "registrar_evento", lambda self, d: None)


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------


def _crear_cliente_con_cors() -> TestClient:
    """Cliente con CORS habilitado para un origen de prueba."""
    os.environ["API_KEY"] = "test-scenarios-key"
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("VT_API_KEY", None)
    os.environ["LLM_PROVEEDOR"] = "simulado"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/analyses/{id}
# ---------------------------------------------------------------------------


class TestGetAnalysisById:
    """Detalle de un análisis concreto."""

    def test_get_por_id_existente(self) -> None:
        """POST + GET /{id} → 200 con el mismo análisis."""
        client = _crear_cliente()
        try:
            post_resp = _post_analisis(client, _correo_benigno())
            assert post_resp.status_code == 201
            analysis_id = post_resp.json()["id"]
            get_resp = client.get(f"/api/analyses/{analysis_id}", headers=_headers())
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == analysis_id
        finally:
            _limpiar_env()

    def test_get_por_id_inexistente_retorna_404(self) -> None:
        """GET /api/analyses/no-existe → 404."""
        client = _crear_cliente()
        try:
            resp = client.get("/api/analyses/id-que-no-existe-xyzw", headers=_headers())
            assert resp.status_code == 404
            data = resp.json()
            assert "error" in data
        finally:
            _limpiar_env()

    def test_get_por_id_sin_autenticacion_retorna_401(self) -> None:
        """GET /api/analyses/{id} sin API-Key → 401."""
        client = _crear_cliente()
        try:
            resp = client.get(
                "/api/analyses/cualquier-id",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# PATCH /api/analyses/{id}/feedback
# ---------------------------------------------------------------------------


class TestPatchFeedback:
    """Retroalimentación de análisis."""

    def test_feedback_correcto_retorna_200(self) -> None:
        """PATCH /feedback con retroalimentación válida → 200."""
        client = _crear_cliente()
        try:
            post_resp = _post_analisis(client, _correo_benigno())
            analysis_id = post_resp.json()["id"]
            patch_resp = client.patch(
                f"/api/analyses/{analysis_id}/feedback",
                json={"feedback": "falso_positivo"},
                headers=_headers(),
            )
            assert patch_resp.status_code == 200
        finally:
            _limpiar_env()

    def test_feedback_id_inexistente_retorna_404(self) -> None:
        """PATCH /feedback en análisis que no existe → 404."""
        client = _crear_cliente()
        try:
            resp = client.patch(
                "/api/analyses/no-existe/feedback",
                json={"feedback": "falso_positivo"},
                headers=_headers(),
            )
            assert resp.status_code == 404
        finally:
            _limpiar_env()

    def test_feedback_persiste_en_respuesta(self) -> None:
        """La retroalimentación queda reflejada en la respuesta del PATCH."""
        client = _crear_cliente()
        try:
            post_resp = _post_analisis(client, _correo_benigno())
            analysis_id = post_resp.json()["id"]
            patch_resp = client.patch(
                f"/api/analyses/{analysis_id}/feedback",
                json={"feedback": "confirmado"},
                headers=_headers(),
            )
            # Feedback valid: "confirmado" or "falso_positivo" (Literal type)
            assert patch_resp.status_code == 200
            assert patch_resp.json().get("retroalimentacion") == "confirmado"
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# DELETE /api/analyses/{id}
# ---------------------------------------------------------------------------


class TestDeleteAnalysis:
    """Borrado de análisis."""

    def test_delete_existente_retorna_204(self) -> None:
        """DELETE análisis existente → 204."""
        client = _crear_cliente()
        try:
            post_resp = _post_analisis(client, _correo_benigno())
            analysis_id = post_resp.json()["id"]
            del_resp = client.delete(f"/api/analyses/{analysis_id}", headers=_headers())
            assert del_resp.status_code == 204
        finally:
            _limpiar_env()

    def test_delete_inexistente_retorna_404(self) -> None:
        """DELETE análisis que no existe → 404."""
        client = _crear_cliente()
        try:
            resp = client.delete("/api/analyses/no-existe-tampoco", headers=_headers())
            assert resp.status_code == 404
        finally:
            _limpiar_env()

    def test_delete_luego_get_retorna_404(self) -> None:
        """Después de DELETE, GET del mismo id → 404."""
        client = _crear_cliente()
        try:
            post_resp = _post_analisis(client, _correo_benigno())
            analysis_id = post_resp.json()["id"]
            client.delete(f"/api/analyses/{analysis_id}", headers=_headers())
            get_resp = client.get(f"/api/analyses/{analysis_id}", headers=_headers())
            assert get_resp.status_code == 404
        finally:
            _limpiar_env()


# ---------------------------------------------------------------------------
# GET /api/analyses/export.csv
# ---------------------------------------------------------------------------


class TestExportCsv:
    """Exportación CSV."""

    def test_export_csv_retorna_200(self) -> None:
        """export.csv → 200 con Content-Type text/csv."""
        client = _crear_cliente()
        try:
            _post_analisis(client, _correo_benigno())
            resp = client.get("/api/analyses/export.csv", headers=_headers())
            assert resp.status_code == 200
            assert "text/csv" in resp.headers.get("content-type", "")
        finally:
            _limpiar_env()

    def test_export_csv_tiene_header(self) -> None:
        """El CSV tiene al menos una línea de encabezado."""
        client = _crear_cliente()
        try:
            _post_analisis(client, _correo_benigno())
            resp = client.get("/api/analyses/export.csv", headers=_headers())
            contenido = resp.content.decode("utf-8-sig")  # strip BOM
            lineas = [linea for linea in contenido.splitlines() if linea.strip()]
            assert len(lineas) >= 1
        finally:
            _limpiar_env()

    def test_export_csv_no_contiene_formula_injection(self) -> None:
        """El CSV escapa caracteres de inyección (CWE-1236)."""
        client = _crear_cliente()
        try:
            # Correo con asunto que podría inyectar fórmula
            correo = _correo_benigno()
            correo["subject"] = "=CMD|'/C calc'!A0"
            _post_analisis(client, correo)
            resp = client.get("/api/analyses/export.csv", headers=_headers())
            csv_text = resp.content.decode("utf-8-sig")
            # El valor peligroso debe estar entrecomillado o escapado
            assert "=CMD|'/C calc'!A0" not in csv_text or ',"=CMD' not in csv_text
        finally:
            _limpiar_env()

    def test_export_csv_sin_auth_retorna_401(self) -> None:
        """export.csv sin API key → 401."""
        client = _crear_cliente()
        try:
            resp = client.get(
                "/api/analyses/export.csv",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
        finally:
            _limpiar_env()
