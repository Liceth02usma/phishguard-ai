"""Guardado de análisis con enmascarado (spec 011, M14, FR-002).

guardar_analisis(analisis, repo) -> str
Persiste el análisis tras verificar que no contiene HTML ni adjuntos.
"""

from __future__ import annotations

import logging

from .modelos import AnalisisPersistido
from .repositorio import RepositorioAnalisis, RepositorioReal

logger = logging.getLogger(__name__)


def guardar_analisis(
    analisis: AnalisisPersistido,
    *,
    repo: RepositorioAnalisis | None = None,
) -> str:
    """Persiste un análisis en MongoDB (FR-002, AC-PER-01).

    Pre-condición: analisis.correo_enmascarado no contiene htmlBody
                    ni contenido de adjuntos.
    Post-condición: documento insertado en phishguard.analyses con TTL.
    Retorna: message_id del análisis guardado.
    """
    # Verificar invariantes I1/I2
    _verificar_sin_html_adjuntos(analisis)

    # Usar repo real si no se proporciona
    repositorio = repo or RepositorioReal()

    # Persistir
    doc = analisis.model_dump(mode="json")
    msg_id = repositorio.guardar(doc)

    logger.info("Análisis guardado: %s", msg_id)
    return msg_id


def _verificar_sin_html_adjuntos(analisis: AnalisisPersistido) -> None:
    """Verifica invariantes I1/I2: no htmlBody ni contenido de adjuntos."""
    correo = analisis.correo_enmascarado

    # I1: no htmlBody
    if "htmlBody" in correo:
        raise ValueError(
            "Invariante I1 violada: correo_enmascarado contiene htmlBody"
        )

    # I2: no contenido de adjunto
    adjuntos = correo.get("adjuntos", [])
    if isinstance(adjuntos, list):
        for adj in adjuntos:
            if isinstance(adj, dict) and "contenido" in adj:
                raise ValueError(
                    "Invariante I2 violada: adjunto contiene contenido"
                )
