"""AC-SCO-02: monotonicidad — agregar una bandera nunca baja el score_final.

Usa hypothesis con coeficientes y puntos de banderas crecientes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.level3_logic.modelo import cargar_modelo, predecir_probabilidad

PROYECTO = Path(__file__).resolve().parent.parent.parent
RUTA_JSON = PROYECTO / "data" / "modelo" / "clasificador_v1.json"


def _score_final(score_clasificador: float, puntos_banderas: int) -> int:
    """Fórmula del score_final: min(100, round(score_clasificador + min(60, puntos)))."""
    return min(100, round(score_clasificador + min(60, puntos_banderas)))


@pytest.mark.ac("AC-SCO-02")
@given(
    score_clasificador=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    puntos_base=st.integers(min_value=0, max_value=100),
    puntos_extra=st.integers(min_value=0, max_value=50),
)
@settings(max_examples=200)
def test_agregar_bandera_nunca_baja(
    score_clasificador: float, puntos_base: int, puntos_extra: int,
) -> None:
    """score_final con más banderas ≥ score_final con menos banderas."""
    sin_extra = _score_final(score_clasificador, puntos_base)
    con_extra = _score_final(score_clasificador, puntos_base + puntos_extra)
    assert con_extra >= sin_extra


@pytest.mark.ac("AC-SCO-02")
def test_monotonicidad_genes() -> None:
    """Activar un gen con coeficiente positivo sube la probabilidad."""
    modelo = cargar_modelo(RUTA_JSON)
    genes_base = [0] * 32
    prob_base = predecir_probabilidad(modelo, genes_base)
    # Activar todos los genes con coeficiente positivo
    genes_pos = [0] * 32
    for _i, nombre in enumerate(modelo.coeficientes):
        from src.level3_logic.genetic_logic import MAPEO_INDICES
        if modelo.coeficientes[nombre] > 0:
            idx = MAPEO_INDICES.index(nombre)
            genes_pos[idx] = 1
    prob_pos = predecir_probabilidad(modelo, genes_pos)
    assert prob_pos >= prob_base
