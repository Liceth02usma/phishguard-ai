"""Análisis estático de adjuntos en memoria (spec 005, módulo M05).

API pública: `analizar_adjunto` analiza un adjunto (bytes en memoria) y
devuelve hashes + banderas del catálogo 5.3. Nunca escribe a disco ni
ejecuta (FR-006, Art. V.5).
"""

from __future__ import annotations

from src.level2_agent.adjuntos.configuracion import ConfigAdjuntos, ConfiguracionError
from src.level2_agent.adjuntos.modelos import (
    ADJ_LIMITE_DESCOMPRIMIDO_ZIP,
    ADJ_LIMITE_ENTRADAS_ZIP,
    ADJ_RATIO_MAXIMO_ZIP,
    CATALOGO_ADJUNTOS,
    AnalisisAdjunto,
    BanderaAdjunto,
)
from src.level2_agent.adjuntos.motor import analizar_adjunto

__all__ = [
    "ADJ_LIMITE_DESCOMPRIMIDO_ZIP",
    "ADJ_LIMITE_ENTRADAS_ZIP",
    "ADJ_RATIO_MAXIMO_ZIP",
    "CATALOGO_ADJUNTOS",
    "AnalisisAdjunto",
    "BanderaAdjunto",
    "ConfigAdjuntos",
    "ConfiguracionError",
    "analizar_adjunto",
]
