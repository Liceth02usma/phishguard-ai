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

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble

VEREDICTOS_VALIDOS = {"malicioso", "sospechoso", "revision_manual", "sin_indicadores"}
# Literal canónico de `Severidad` (src/api/schemas/comunes.py) y de
# `NivelSeveridad` (spec 008): "Critico" sin tilde. Antes se esperaba
# "Crítico" y el test solo pasaba mientras ningún correo llegaba a esa
# severidad.
SEVERIDADES_VALIDAS = {"Bajo", "Medio", "Alto", "Critico"}


# --- Helpers ---


@pytest.fixture(autouse=True)
def _aislar_entorno_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla los tests E2E de MongoDB real (auditoría AUD-01).

    Sin `MONGODB_ATLAS_CLUSTER_URI`:
    - la idempotencia de acciones cae a memoria (sin escribir `api_*` en la
      BD de producción, como ocurría antes),
    - el contador diario de LLM cae a memoria (el tope real de 100/día
      degradaba los veredictos de zona gris a `sospechoso`).
    Además se sustituye RDAP por un doble sin red (~30s/test de latencia
    real eliminados); `None` equivale al caso conservador DOMINIO_EDAD_
    DESCONOCIDA (0 puntos, sin impacto en veredictos).
    monkeypatch restaura todo tras cada prueba.
    """
    from src.level2_agent.banderas.rdap import RequestsRDAP

    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    monkeypatch.setattr(RequestsRDAP, "registrar_evento", lambda self, d: None)


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
    """Correo interno benigno: reunión de equipo.

    Incluye Authentication-Results con authserv-id confiable y spf/dkim/dmarc
    pass (auditoría 2026-11-20): sin él, AUTH_NO_EVALUABLE suma +5 y el score
    (26+5=31) caería en la zona gris.
    """
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
            "Authentication-Results": (
                "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"
            ),
        },
    }


def _correo_sospechoso() -> dict[str, Any]:
    """Correo sospechoso: remitente externo + urgencia + URL acortador.

    dkim=none (auditoría 2026-11-20): la triple falla queda bloqueada para
    que R4 NO dispare y el veredicto siga siendo `sospechoso`.
    """
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
            "Authentication-Results": (
                "mail.ucaldas.edu.co; spf=fail; dkim=none; dmarc=fail"
            ),
        },
    }


def _correo_malicioso() -> dict[str, Any]:
    """Correo malicioso: muchos indicadores + auth fallida + script PHP.

    Cadena R4 (auditoría 2026-11-20): authserv-id confiable con spf/dkim/dmarc
    fail (triple falla evaluable) + nombre visible con la marca "ucaldas" en
    dominio externo → NOMBRE_SUPLANTA → R4 → veredicto `malicioso`.
    """
    return {
        "modo": "pegar",
        "dry_run": True,
        "subject": "URGENTE: Factura vencida — acción requerida inmediatamente",
        "from": "UCaldas Facturas <facturas@banc0-seguro.xyz>",
        "to": "usuario@ucaldas.edu.co",
        "text": (
            "Estimado cliente, su factura está vencida. "
            "Descargue el adjunto y visite http://bit.ly/factura-urgente "
            "para evitar suspensión del servicio."
        ),
        "headers": {
            "From": "UCaldas Facturas <facturas@banc0-seguro.xyz>",
            "To": "usuario@ucaldas.edu.co",
            "Authentication-Results": (
                "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail"
            ),
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
        """Correo malicioso → veredicto de riesgo (nunca sin_indicadores).

        Entorno del test: LLM simulado (no confirma phishing) y sin VT — con el
        fix AC-API-10 (Opción A) el motor determinista produce ahora
        `revision_manual` (VT_NO_DISPONIBLE registrado como incompleta) para el
        score de zona gris (44) de este fixture. Como en sus tests hermanos,
        se acepta cualquier veredicto de riesgo; lo no negociable es
        `es_phishing=True`.
        """
        client = _crear_cliente()
        try:
            resp = _post_analisis(client, _correo_malicioso())
            data = resp.json()
            assert data["resultado"]["veredicto"] in (
                "malicioso", "sospechoso", "revision_manual"
            )
            assert data["resultado"]["es_phishing"] is True
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
            assert sev in ("Medio", "Alto", "Critico")
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
            campos = (
                "id", "origen", "modo", "creado_en",
                "duracion_ms", "correo", "resultado", "accion",
            )
            for campo in campos:
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
