"""Borrado de análisis y caché VT asociada (spec 011, M14, FR-005).

borrar_analisis(message_id, repo, cache_vt) -> bool
Elimina el documento de analyses y entradas de vt_cache.
"""

from __future__ import annotations

import logging

from .repositorio import RepositorioAnalisis, RepositorioCacheVT

logger = logging.getLogger(__name__)


def borrar_analisis(
    message_id: str,
    *,
    repo: RepositorioAnalisis,
    cache_vt: RepositorioCacheVT | None = None,
) -> bool:
    """Elimina un análisis y su caché VT asociada (FR-005, AC-PER-07).

    Retorna: True si se eliminó, False si no existía.
    """
    # 1. Borrar documento de analyses
    borrado = repo.borrar(message_id)

    if not borrado:
        return False

    # 2. Borrar caché VT asociada (best-effort)
    if cache_vt is not None:
        try:
            n = cache_vt.borrar_por_message_id(message_id)
            if n > 0:
                logger.info(
                    "Borradas %d entradas de caché VT para %s",
                    n,
                    message_id,
                )
        except Exception as e:
            logger.warning(
                "Error borrando caché VT para %s: %s",
                message_id,
                e,
            )

    return True
