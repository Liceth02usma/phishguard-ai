"""Guardado de análisis con enmascarado (spec 011, M14, FR-002).

guardar_analisis(analisis, repo) -> str
Persiste el análisis tras verificar que no contiene HTML ni adjuntos.
Auditoría AUD-03: reintenta con backoff exponencial ante fallos transitorios
de MongoDB ("No primary available for writes" observado en producción).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from .modelos import AnalisisPersistido
from .repositorio import RepositorioAnalisis, RepositorioReal

logger = logging.getLogger(__name__)

REINTENTOS_DEFECTO: int = 3
"""Intentos totales de guardado (1 inicial + 2 reintentos)."""

ESPERA_BASE_SEGUNDOS: float = 0.5
"""Espera base del backoff: 0.5s, 1s (exponencial)."""


def guardar_analisis(
    analisis: AnalisisPersistido,
    *,
    repo: RepositorioAnalisis | None = None,
    reintentos: int = REINTENTOS_DEFECTO,
    dormir: Callable[[float], None] = time.sleep,
) -> str:
    """Persiste un análisis en MongoDB (FR-002, AC-PER-01).

    Pre-condición: analisis.correo_enmascarado no contiene htmlBody
                    ni contenido de adjuntos.
    Post-condición: documento insertado en phishguard.analyses con TTL.
    Retorna: message_id del análisis guardado.
    Lanza: la última excepción si todos los intentos fallan.
    """
    # Verificar invariantes I1/I2
    _verificar_sin_html_adjuntos(analisis)

    # Usar repo real si no se proporciona
    repositorio = repo or RepositorioReal()

    # Persistir con reintento ante fallos transitorios (AUD-03)
    doc = analisis.model_dump(mode="json")
    ultimo_error: Exception | None = None
    for intento in range(max(1, reintentos)):
        try:
            msg_id = repositorio.guardar(doc)
            logger.info("Análisis guardado: %s", msg_id)
            return msg_id
        except Exception as exc:
            ultimo_error = exc
            if intento < reintentos - 1:
                espera = ESPERA_BASE_SEGUNDOS * (2**intento)
                logger.warning(
                    "Guardado falló (intento %d/%d): %s — reintento en %.1fs",
                    intento + 1,
                    reintentos,
                    exc,
                    espera,
                )
                dormir(espera)
    assert ultimo_error is not None
    raise ultimo_error


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
