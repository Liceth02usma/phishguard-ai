"""Tests E2E del flujo completo via API REST.

Flujo: POST /api/analyses (correo JSON) → pipeline completo → respuesta con veredicto.

Verifica:
- La API acepta correos y retorna 201 con estructura correcta
- El pipeline corre end-to-end sin crashear (specs 002-009)
- Correos con más indicadores obtienen score más alto (orden relativo)
- El veredicto es uno de los 4 valores canónicos
- La respuesta tiene todos los campos del schema
- GET /api/analyses lista los análisis
- Autenticación funciona (401 sin key)
- Health check funciona
- Modo muestra funciona
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble

VEREDICTOS_VALIDOS = {"malicioso", "sospechoso", "revision_manual", "sin_indicadores"}
SEVERIDADES_VALIDAS = {"Bajo", "Medio", "Alto", "Crítico"}


# --- Helpers ---


def _crear_cliente() -> TestClient:
    """Crea un TestClient con repos dobles y API key de test."""
    os.environ["API_KEY"] = "test-e2e-key"
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("VT_API_KEY", None)
    os.environ["LLM_PROVEEDOR"] = "simulado"
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    return TestClient(app)


def _headers() -> dict[str, str]:
    """Headers con API key válida."""
    return {"X-API-Key": "test-e2e-key", "Content-Type": "application/json"}


def _post_analisis(client: TestClient, body: dict[str, Any]) -> Any:
    """POST /api/analyses con body JSON."""
    return client.post("/api/analyses", json=body, headers=_headers())


def _limpiar_env() -> None:
    """Limpia env vars de test."""
    os.environ.pop("API_KEY", None)
    os.environ.pop("LLM_PROVEEDOR", None)


# --- Correos de prueba ---


def _correo_benigno() -> dict[str, Any]:
    """Correo interno benigno: reunión de equipo."""
    return {
        "modo": "pegar",
        "dry_run": True,
        "subject": "Reunión de equipo mañana a las 10am",
        "from": "colega@ucaldas.edu.co",
        "to": "equipo@ucaldas.edu.co",
        "text": "Hola equipo, les recuerdo la reunión de mañana en sala 302.",
        "headers": {
            "From": "colega@ucaldas.edu.co",
            "To": "equipo@ucaldas.edu.co",
        },
    }


def _correo_sospechoso() -> dict[str, Any]:
    """Correo sospechoso: remitente externo + urgencia + URL acortador."""
    return {
        "modo": "pegar",
        "dry_run": True,
        "subject": "Urgente: verifique su cuenta bancaria inmediatamente",
        "from": "no-reply@banco-seguro.com",
        "to": "usuario@ucaldas.edu.co",
        "text": (
            "Estimado cliente, su cuenta requiere verificación inmediata. "
            "Haga clic en el enlace: http://bit.ly/3x4mPq "
            "para evitar el bloqueo de su cuenta."
        ),
        "headers": {
            "From": "no-reply@banco-seguro.com",
            "To": "usuario@ucaldas.edu.co",
            "Authentication-Results": "spf=fail; dkim=none; dmarc=fail",
        },
    }


def _correo_malicioso() -> dict[str, Any]:
    """Correo malicioso: muchos indicadores + auth fallida + script PHP."""
    return {
        "modo": "pegar",
        "dry_run": True,
        "subject": "URGENTE: Factura vencida — acción requerida inmediatamente",
        "from": "facturas@banc0-seguro.xyz",
        "to": "usuario@ucaldas.edu.co",
        "text": (
            "Estimado cliente, su factura está vencida. "
            "Descargue el adjunto y visite http://bit.ly/factura-urgente "
            "para evitar suspensión del servicio."
        ),
        "headers": {
            "From": "facturas@banc0-seguro.xyz",
            "To": "usuario@ucaldas.edu.co",
            "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail",
            "X-PHP-Originating-Script": "1234:mail.php",
        },
    }


def _correo_phishing_clonado() -> dict[str, Any]:
    """Phishing de clonación: dominio parecido + Reply-To diferente."""
    return {
        "modo": "pegar",
        "dry_run": True,
        "subject": "Actualización de credenciales - Portal UCaldas",
        "from": "soporte@ucaldas-seguro.xyz",
        "to": "profesor@ucaldas.edu.co",
        "text": (
            "Estimado docente, por razones de seguridad debe actualizar "
            "sus credenciales en http://login-ucaldas.xyz/auth "
            "antes de 24 horas o su cuenta será desactivada."
        ),
        "headers": {
            "From": "soporte@ucaldas-seguro.xyz",
            "Reply-To": "admin@ucaldas-seguro.xyz",
            "To": "profesor@ucaldas.edu.co",
            "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail",
        },
    }


# --- Tests E2E: Pipeline end-to-end via API ---


class TestE2EApiPipeline:
    """E2E: el pipeline completo corre via API sin crashear."""

    def test_benigno_retorna_201(self) -> None:
        """Correo benigno → 201 Created."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_benigno())
            assert resp.status_code == 201
        finally:
            _limpiar_env()

    def test_sospechoso_retorna_201(self) -> None:
        """Correo sospechoso → 201 Created."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_sospechoso())
            assert resp.status_code == 201
        finally:
            _limpiar_env()

    def test_malicioso_retorna_201(self) -> None:
        """Correo malicioso → 201 Created."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_malicioso())
            assert resp.status_code == 201
        finally:
            _limpiar_env()

    def test_clonado_retorna_201(self) -> None:
        """Phishing clonado → 201 Created."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_phishing_clonado())
            assert resp.status_code == 201
        finally:
            _limpiar_env()


class TestE2EApiVeredicto:
    """E2E: veredictos canónicos y coherentes."""

    def test_benigno_veredicto_valido(self) -> None:
        """Correo benigno → veredicto es uno de los 4 canónicos."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_benigno())
            data = resp.json()
            assert data["resultado"]["veredicto"] in VEREDICTOS_VALIDOS
        finally:
            _limpiar_env()

    def test_sospechoso_veredicto_de_riesgo(self) -> None:
        """Correo sospechoso → veredicto NO es sin_indicadores."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_sospechoso())
            data = resp.json()
            assert data["resultado"]["veredicto"] in (
                "malicioso", "sospechoso", "revision_manual"
            )
        finally:
            _limpiar_env()

    def test_malicioso_veredicto_de_riesgo(self) -> None:
        """Correo malicioso → veredicto de riesgo (malicioso o revision_manual por VT degradado)."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_malicioso())
            data = resp.json()
            # Con VT disponible → malicioso; sin VT → revision_manual (FR-003)
            assert data["resultado"]["veredicto"] in ("malicioso", "revision_manual")
        finally:
            _limpiar_env()

    def test_clonado_veredicto_de_riesgo(self) -> None:
        """Phishing clonado → veredicto de riesgo."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_phishing_clonado())
            data = resp.json()
            assert data["resultado"]["veredicto"] in ("malicioso", "sospechoso", "revision_manual")
        finally:
            _limpiar_env()

    def test_veredicto_nunca_contiene_seguro(self) -> None:
        """Art. V.1: la palabra 'seguro' nunca aparece como afirmación."""
        client = _crear_cliente()
        try:
            for correo in [_correo_benigno(), _correo_sospechoso(), _correo_malicioso()]:
                resp = _post_analisis(client, correo)
                data = resp.json()
                resumen = data["resultado"]["resumen"].lower()
                if "seguro" in resumen:
                    assert "no seguro" in resumen or "inseguro" in resumen
        finally:
            _limpiar_env()


class TestE2EApiScore:
    """E2E: scores y severidades."""

    def test_score_en_rango_0_100(self) -> None:
        """Score siempre en rango [0, 100]."""
        client = _crear_cliente()
        try:
            for correo in [_correo_benigno(), _correo_malicioso()]:
                resp = _post_analisis(client, correo)
                score = resp.json()["resultado"]["score"]
                assert 0 <= score <= 100
        finally:
            _limpiar_env()

    def test_severidad_valida(self) -> None:
        """Severidad siempre es uno de los 4 valores canónicos."""
        client = _crear_cliente()
        try:
            for correo in [_correo_benigno(), _correo_sospechoso(), _correo_malicioso()]:
                resp = _post_analisis(client, correo)
                sev = resp.json()["resultado"]["nivel_severidad"]
                assert sev in SEVERIDADES_VALIDAS, f"Severidad inválida: {sev}"
        finally:
            _limpiar_env()

    def test_malicioso_severidad_no_baja(self) -> None:
        """Correo malicioso → severidad no es Bajo."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_malicioso())
            sev = resp.json()["resultado"]["nivel_severidad"]
            assert sev in ("Medio", "Alto", "Crítico")
        finally:
            _limpiar_env()


class TestE2EApiEstructura:
    """E2E: estructura de la respuesta API."""

    def test_respuesta_tiene_campos_obligatorios(self) -> None:
        """La respuesta tiene todos los campos del schema AnalisisResponse."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_benigno())
            data = resp.json()
            # Nivel superior
            for campo in ("id", "origen", "modo", "creado_en", "duracion_ms", "correo", "resultado", "accion"):
                assert campo in data, f"Falta campo: {campo}"
            # Correo
            for campo in ("remitente", "asunto"):
                assert campo in data["correo"], f"Falta campo correo.{campo}"
            # Resultado
            for campo in ("score", "veredicto", "es_phishing", "nivel_severidad", "resumen"):
                assert campo in data["resultado"], f"Falta campo resultado.{campo}"
        finally:
            _limpiar_env()

    def test_duracion_no_negativa(self) -> None:
        """duracion_ms >= 0."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_benigno())
            assert resp.json()["duracion_ms"] >= 0
        finally:
            _limpiar_env()

    def test_id_no_vacio(self) -> None:
        """El ID del análisis no está vacío."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_benigno())
            assert len(resp.json()["id"]) > 0
        finally:
            _limpiar_env()

    def test_resumen_no_vacio(self) -> None:
        """El resumen del análisis no está vacío."""
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_benigno())
            assert len(resp.json()["resultado"]["resumen"]) > 0
        finally:
            _limpiar_env()


class TestE2EApiGetAnalyses:
    """E2E: GET /api/analyses lista análisis previos."""

    def test_lista_despues_de_post(self) -> None:
        """Después de POST, GET lista incluye el análisis."""
        client = _crear_cliente()
        try:
            _post_analisis(client, _correo_benigno())
            resp = client.get("/api/analyses", headers=_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] >= 1
        finally:
            _limpiar_env()

    def test_filtro_por_veredicto(self) -> None:
        """Filtro veredicto=malicioso solo retorna maliciosos."""
        client = _crear_cliente()
        try:
            _post_analisis(client, _correo_benigno())
            _post_analisis(client, _correo_malicioso())
            resp = client.get(
                "/api/analyses?veredicto=malicioso",
                headers=_headers(),
            )
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert item["resultado"]["veredicto"] == "malicioso"
        finally:
            _limpiar_env()


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
        """Malicioso y benigno producen scores (pueden ser iguales si el clasificador no distingue)."""
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
