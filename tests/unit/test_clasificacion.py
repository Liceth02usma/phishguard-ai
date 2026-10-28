"""Tabla de decisión pura `clasificar_stats` (FR-007, M06.4): casos y umbrales propios."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import ConfigVT, LastAnalysisStats, clasificar_stats

MALIGNOS = 3  # UMBRAL_MALICIOSA literal de M06.4
SOSPECHOSOS = 3  # UMBRAL_SOSPECHOSA literal de M06.4
LIMPIOS = 20  # UMBRAL_LIMPIA literal de M06.4


@pytest.mark.ac("AC-VT-08")
@pytest.mark.parametrize(
    ("stats", "esperado"),
    [
        (LastAnalysisStats(malicious=5, harmless=0, undetected=0), "maliciosa"),
        (LastAnalysisStats(malicious=3, harmless=0, undetected=0), "maliciosa"),
        (LastAnalysisStats(malicious=2, harmless=0, undetected=0), "sospechosa"),
        (LastAnalysisStats(malicious=1, harmless=0, undetected=0), "sospechosa"),
        (LastAnalysisStats(malicious=0, suspicious=4, harmless=0, undetected=0), "sospechosa"),
        (LastAnalysisStats(malicious=0, suspicious=3, harmless=0, undetected=0), "sospechosa"),
        (LastAnalysisStats(malicious=0, suspicious=2, harmless=0, undetected=0), "desconocida"),
        (LastAnalysisStats(malicious=0, suspicious=0, harmless=19, undetected=0), "desconocida"),
        (LastAnalysisStats(malicious=0, suspicious=0, harmless=0, undetected=20), "limpia"),
        (LastAnalysisStats(malicious=0, suspicious=0, harmless=10, undetected=10), "limpia"),
        (LastAnalysisStats(malicious=2, suspicious=2, harmless=10, undetected=10), "sospechosa"),
        (LastAnalysisStats(), "desconocida"),  # stats sin ningún apoyo
        (None, "desconocida"),  # sin stats (404/respuesta inesperada)
    ],
)
def test_tabla_decision_completa(stats: LastAnalysisStats | None, esperado: str) -> None:
    """Las 13 combinaciones de la tabla M06.4 + ausencia de stats (FR-007)."""
    assert clasificar_stats(stats, ConfigVT()) == esperado


@pytest.mark.ac("AC-VT-08")
@pytest.mark.parametrize(
    ("stats", "esperado"),
    [
        (LastAnalysisStats(malicious=1, harmless=0, undetected=0), "maliciosa"),  # umbral propio 1
        (LastAnalysisStats(malicious=0, suspicious=2, harmless=0, undetected=0), "sospechosa"),
        (LastAnalysisStats(malicious=0, suspicious=0, harmless=5, undetected=0), "limpia"),  # 5
        (LastAnalysisStats(malicious=0, suspicious=0, harmless=4, undetected=0), "desconocida"),
    ],
)
def test_umbrales_configurables_por_consumidor(stats: LastAnalysisStats, esperado: str) -> None:
    """FR-007: la tabla usa los umbrales del consumidor (no siempre 3/3/20)."""
    config = ConfigVT(umbral_maliciosa=1, umbral_sospechosa=2, umbral_limpia=5)
    assert clasificar_stats(stats, config) == esperado
