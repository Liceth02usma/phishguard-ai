"""Tabla de decisión pura de clasificación (spec 006, FR-007, M06.4).

Función sin E/S: `clasificar_stats(stats, config)`. Los umbrales por defecto
(3/3/20) son LITERALES de M06.4; el consumidor puede pasar los suyos en
`config` (FR-007 — la tabla usa los umbrales del consumidor, no siempre 3/3/20).
"""

from __future__ import annotations

from src.level2_agent.virustotal.configuracion import ConfigVT
from src.level2_agent.virustotal.modelos import Clasificacion, LastAnalysisStats


def clasificar_stats(
    stats: LastAnalysisStats | None, config: ConfigVT | None = None
) -> Clasificacion:
    """Aplica la tabla M06.4: `maliciosa` / `sospechosa` / `limpia` / `desconocida`.

    - `stats is None` (404 o sin `last_analysis_stats`) → `desconocida`.
    - `malicious >= umbral_maliciosa` → `maliciosa`.
    - `malicious >= 1` o `suspicious >= umbral_sospechosa` → `sospechosa`.
    - `harmless + undetected >= umbral_limpia` → `limpia`.
    - En otro caso → `desconocida` (nunca se reporta `limpia` sin apoyos).
    """
    if stats is None:
        return "desconocida"
    cfg = config if config is not None else ConfigVT()
    if stats.malicious >= cfg.umbral_maliciosa:
        return "maliciosa"
    if stats.malicious >= 1 or stats.suspicious >= cfg.umbral_sospechosa:
        return "sospechosa"
    if stats.harmless + stats.undetected >= cfg.umbral_limpia:
        return "limpia"
    return "desconocida"
