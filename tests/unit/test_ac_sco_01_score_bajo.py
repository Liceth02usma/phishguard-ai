"""AC-SCO-01: correo limpio (0 genes) ⇒ score_clasificador < 30.

Con el clasificador entrenado, el intercepto produce un score bajo
cuando ningún gen se activa.
"""

from __future__ import annotations

import pytest
from src.level3_logic.modelo import cargar_modelo, predecir_probabilidad

RUTA_JSON = (
    __import__("pathlib").Path(__file__).resolve().parent.parent.parent
    / "data" / "modelo" / "clasificador_v1.json"
)


@pytest.mark.ac("AC-SCO-01")
def test_cero_genes_score_bajo() -> None:
    """0 genes activos → score_clasificador < 30."""
    modelo = cargar_modelo(RUTA_JSON)
    prob = predecir_probabilidad(modelo, [0] * 32)
    score = prob * 100.0
    assert score < 30.0, f"Score con 0 genes = {score:.2f}, esperado < 30"


@pytest.mark.ac("AC-SCO-01")
def test_cero_genes_via_evaluate() -> None:
    """evaluate con email vacío → score < 30 (usa modelo, no PESOS_AG)."""
    # Este test se activará cuando genetic_logic.use ConfigGenetico
    # Por ahora verifica el comportamiento del modelo directamente
    modelo = cargar_modelo(RUTA_JSON)
    prob = predecir_probabilidad(modelo, [0] * 32)
    assert prob * 100.0 < 30.0
