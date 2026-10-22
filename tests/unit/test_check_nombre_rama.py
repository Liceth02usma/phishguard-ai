"""Pruebas para la compuerta de nombre de rama (AC-CAL-02).

Tabla de decisión: nombres válidos e inválidos.
"""

from __future__ import annotations

import pytest
from scripts.check_nombre_rama import evaluar_nombre_rama

NOMBRES_VALIDOS = [
    "feature/analisis-urls",
    "fix/x",
    "chore/a-b-c",
    "refactor/eliminar-memoria",
    "test/conjunto-evaluacion",
    "docs/readme",
]

NOMBRES_INVALIDOS = [
    "Feature/x",          # mayúscula
    "feature/Analisis",   # mayúscula en nombre
    "001-analisis",       # prefijo numérico, sin tipo
    "feature/",           # nombre vacío
    "feature/a_b",        # guion bajo
    "feature/a b",        # espacio
    "hotfix/x",           # tipo no permitido
    "feature/Análisis",   # tilde
]


@pytest.mark.ac("AC-CAL-02")
@pytest.mark.parametrize("rama", NOMBRES_VALIDOS)
def test_nombres_validos_pasan(rama: str) -> None:
    resultado = evaluar_nombre_rama(rama)
    assert resultado.ok is True, f"Esperaba que {rama!r} pasara"


@pytest.mark.ac("AC-CAL-02")
@pytest.mark.parametrize("rama", NOMBRES_INVALIDOS)
def test_nombres_invalidos_fallan(rama: str) -> None:
    resultado = evaluar_nombre_rama(rama)
    assert resultado.ok is False, f"Esperaba que {rama!r} fallara"


@pytest.mark.ac("AC-CAL-02")
@pytest.mark.parametrize("rama", ["main", "develop"])
def test_ramas_exentas_pasan(rama: str) -> None:
    """main y develop están exentas (Art. I.4)."""
    resultado = evaluar_nombre_rama(rama)
    assert resultado.ok is True
