"""Motor de scoring: calcular_score_final (spec 007, contrato §3).

Orquesta clasificador lineal + banderas (003/004/005) en 8 pasos.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.level2_agent.banderas import ResultadoBanderas, evaluar_banderas
from src.level2_agent.banderas.modelos import TOPE_PUNTOS_BANDERAS
from src.level2_agent.analisis_urls import analizar_urls, ResultadoURLs, DependenciasURLs, dependencias_por_defecto
from src.level2_agent.adjuntos.modelos import AnalisisAdjunto
from src.level2_agent.models import EmailData
from src.level3_logic.genetic_logic import evaluate, ConfigGenetico
from src.level3_logic.modelo import cargar_modelo, ClasificadorLineal, ModeloError

from .configuracion import ConfigScoring
from .modelos import BanderaScoring, GenImplicado, ScoreFinal, ScoringError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DependenciasScoring:
    """Dependencias inyectables para el scoring (Art. II.5: cero red en tests).

    Defaults de producción: cliente_rdap real, deps_urls reales, ahora actual.
    """

    cliente_rdap: Any = None
    deps_urls: DependenciasURLs = field(default_factory=dependencias_por_defecto)
    ahora: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def calcular_score_final(
    email_data: EmailData,
    config: ConfigScoring | None = None,
    deps: DependenciasScoring | None = None,
    adjuntos_analizados: Sequence[AnalisisAdjunto] = (),
) -> ScoreFinal:
    """Calcula el score final del email (contrato §3, 8 pasos).

    1. Cargar modelo → version_modelo.
    2. evaluate() con ConfigGenetico → score_clasificador + genes_implicados.
    3. evaluar_banderas() → puntos_totales.
    4. analizar_urls() → Σ banderas[].puntos.
    5. Σ adjuntos_analizados[].banderas[].puntos.
    6. puntos_banderas = min(TOPE_PUNTOS_BANDERAS, suma).
    7. score_final = min(100, round(score_clasificador + puntos_banderas)).
    8. BanderaScoring agregadas en orden estable.

    Args:
        email_data: correo normalizado.
        config: configuración (default: desde entorno).
        deps: dependencias inyectables (default: producción).
        adjuntos_analizados: análisis de adjuntos (inyectados, D7).

    Returns:
        ScoreFinal validado.

    Raises:
        ModeloError: si el modelo no se puede cargar.
        ScoringError: si la configuración es inválida.
    """
    if config is None:
        config = ConfigScoring()
    if deps is None:
        deps = DependenciasScoring()

    # Paso 1: Cargar modelo
    modelo = cargar_modelo(config.ruta_modelo)
    version_modelo = modelo.version

    # Paso 2: Clasificador lineal (genes)
    config_gen = ConfigGenetico(
        modelo=modelo,
        dominios_propios=config.dominios_propios,
        proveedores_confianza=config.proveedores_confianza,
    )
    datos_legacy = _email_data_to_legacy(email_data)
    resultado_gen = evaluate(datos_legacy, config=config_gen)
    score_clasificador = resultado_gen["score"]
    genes_implicados = [
        GenImplicado(caracteristica=g["caracteristica"], peso=g["peso"])
        for g in resultado_gen.get("genes_implicados", [])
    ]

    # Paso 3: Banderas de cabeceras (spec 003)
    banderas_lista: list[BanderaScoring] = []
    puntos_cabeceras = 0
    try:
        from src.level2_agent.banderas import evaluar_banderas as _eval_banderas
        from src.level2_agent.banderas.configuracion import ConfigBanderas
        config_band = ConfigBanderas.desde_entorno()
        resultado_band: ResultadoBanderas = _eval_banderas(
            email_data, config=config_band, ahora=deps.ahora, cliente_rdap=deps.cliente_rdap,
        )
        puntos_cabeceras = resultado_band.puntos_totales
        for b in resultado_band.banderas:
            banderas_lista.append(BanderaScoring(
                origen="cabeceras", codigo=b.codigo, puntos=b.puntos,
            ))
    except Exception as exc:
        logger.warning("Banderas degradadas: %s", exc)

    # Paso 4: URLs (spec 004)
    puntos_urls = 0
    try:
        resultado_urls: ResultadoURLs = analizar_urls(email_data, deps=deps.deps_urls)
        for url in resultado_urls.urls:
            for b in url.banderas:
                puntos_urls += b.puntos
                banderas_lista.append(BanderaScoring(
                    origen="urls", codigo=b.codigo, puntos=b.puntos,
                ))
    except Exception as exc:
        logger.warning("URLs degradadas: %s", exc)

    # Paso 5: Adjuntos (spec 005, inyectados)
    puntos_adjuntos = 0
    for adj in adjuntos_analizados:
        for b in adj.banderas:
            puntos_adjuntos += b.puntos
            banderas_lista.append(BanderaScoring(
                origen="adjuntos", codigo=b.codigo, puntos=b.puntos,
            ))

    # Paso 6: Tope de puntos_banderas
    puntos_banderas = min(TOPE_PUNTOS_BANDERAS, puntos_cabeceras + puntos_urls + puntos_adjuntos)

    # Paso 7: Score final
    score_final = min(100, round(score_clasificador + puntos_banderas))

    # Paso 8: Retornar ScoreFinal validado
    return ScoreFinal(
        score_final=score_final,
        score_clasificador=round(score_clasificador, 2),
        puntos_banderas=puntos_banderas,
        version_modelo=version_modelo,
        genes_implicados=genes_implicados,
        banderas=sorted(banderas_lista),
    )


def _email_data_to_legacy(email_data: EmailData) -> dict[str, Any]:
    """Convierte EmailData a dict legacy para genetic_logic.evaluate."""
    return {
        "htmlBody": email_data.htmlBody or "",
        "textBody": email_data.textBody or "",
        "subject": email_data.subject or "",
        "recipient": email_data.recipient or "",
        "headers": email_data.headers or "{}",
    }
