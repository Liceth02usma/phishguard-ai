"""Conversores y utilidades del endpoint de análisis (spec 012).

Viven fuera de ``routers/analisis.py`` porque la compuerta
``longitud_archivos`` (Art. VI) limita cada fichero de ``src/`` a
:data:`scripts._comunes.LIMITE_LINEAS` (500) líneas.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal, cast

from src.api.eml_parser import extraer_adjuntos_eml
from src.api.schemas.analisis import AdjuntoResponse, AnalisisResponse
from src.level2_agent.decision.modelos import Ruta
from src.level2_agent.models import SCORE_UMBRAL_ALTO, SCORE_UMBRAL_BAJO


def ruta_desde_score(score: int) -> Ruta:
    """Ruta de decisión derivada del score (A4).

    Antes estaba hardcodeada a ``"ia"``, por lo que toda respuesta decía
    ``ruta=ia`` aunque el correo fuera benigno o bloqueado por reglas.

    - score < 30  -> ``heuristica`` (ruta benigna, solo scoring)
    - 30..75      -> ``ia`` (zona gris: agente IA + motor de decisión)
    - score > 75  -> ``reglas`` (bloqueo directo del pipeline)
    """
    if score < SCORE_UMBRAL_BAJO:
        return "heuristica"
    if score > SCORE_UMBRAL_ALTO:
        return "reglas"
    return "ia"


def headers_como_dict(raw: object) -> dict[str, str]:
    """Normaliza ``headers`` (dict o JSON string) a ``dict[str, str]``.

    Los fixtures de ``tests/fixtures/*.json`` guardan ``headers`` como cadena
    JSON; el endpoint acepta dict. Se normaliza una sola vez aquí.
    """
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    if isinstance(raw, str) and raw.strip():
        try:
            datos = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(datos, dict):
            return {str(k): str(v) for k, v in datos.items()}
    return {}


def persistido_a_response(doc: dict[str, Any]) -> AnalisisResponse:
    """Convierte un documento persistido en :class:`AnalisisResponse`."""
    from src.api.schemas.analisis import (
        AccionResponse,
        CorreoResponse,
        ResultadoResponse,
    )

    correo = doc.get("correo_enmascarado", {})
    resultado = doc.get("resultado", {})

    # Mapear modo de persistencia a modo de API
    modo_raw = doc.get("modo", "produccion")
    modo_api = cast(
        Literal["pegar", "eml", "muestra", "gmail"],
        "pegar" if modo_raw in ("produccion", "dry_run") else modo_raw,
    )

    return AnalisisResponse(
        id=str(doc.get("message_id", "")),
        origen=doc.get("origen", "api"),
        modo=modo_api,
        creado_en=doc.get("fecha", datetime.now(tz=UTC)),
        duracion_ms=doc.get("duracion_ms", 0),
        correo=CorreoResponse(
            remitente=correo.get("remitente", ""),
            asunto=correo.get("asunto", ""),
            cuerpo_enmascarado=correo.get("texto_limpio", ""),
        ),
        resultado=ResultadoResponse(
            score=doc.get("score_final", 0),
            ruta=doc.get("ruta", "heuristica"),
            es_phishing=doc.get("veredicto") in ("malicioso", "sospechoso", "revision_manual"),
            veredicto=doc.get("veredicto", "sin_indicadores"),
            nivel_severidad=doc.get("nivel_severidad", "Bajo"),
            resumen=resultado.get("resumen", ""),
        ),
        accion=AccionResponse(
            ejecutada=doc.get("accion"),
            simulada=modo_raw == "dry_run",
        ),
        retroalimentacion=doc.get("retroalimentacion"),
    )


def analizar_adjuntos_eml(contenido: bytes) -> list[AdjuntoResponse]:
    """Extrae adjuntos del EML y los analiza con spec 005 (AC-API-02).

    Devuelve lista de :class:`AdjuntoResponse` con SHA-256 y reputación.
    Los errores de análisis se ignoran (degradación graceful).
    """
    from src.level2_agent.adjuntos import analizar_adjunto

    resultado: list[AdjuntoResponse] = []
    for adj in extraer_adjuntos_eml(contenido):
        try:
            analisis = analizar_adjunto(
                nombre=adj.nombre,
                tipo_declarado=adj.tipo_declarado,
                payload=adj.payload,
            )
            resultado.append(
                AdjuntoResponse(
                    nombre=analisis.nombre,
                    tipo_real=analisis.tipo_real,
                    sha256=analisis.sha256,
                    tamano=analisis.tamano_bytes,
                    reputacion="desconocida",
                )
            )
        except Exception:
            # Degradación: adjunto no analizable → omitir
            pass
    return resultado
