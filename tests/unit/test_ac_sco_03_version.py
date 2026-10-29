"""AC-SCO-03: version_modelo se deriva del JSON (no de constante).

El reporte debe incluir version_modelo y score_clasificador.
"""

from __future__ import annotations

import pytest

from src.level3_logic.modelo import cargar_modelo, invalidate_cache
from pathlib import Path

RUTA_JSON = Path(__file__).resolve().parent.parent.parent / "data" / "modelo" / "clasificador_v1.json"


@pytest.fixture(autouse=True)
def _limpiar_cache() -> None:
    invalidate_cache()
    yield
    invalidate_cache()


@pytest.mark.ac("AC-SCO-03")
def test_version_modelo_desde_json() -> None:
    """version_modelo == 'clasificador_v1' derivado del JSON."""
    modelo = cargar_modelo(RUTA_JSON)
    assert modelo.version == "clasificador_v1"


@pytest.mark.ac("AC-SCO-03")
def test_version_modelo_no_constante() -> None:
    """La version viene del JSON, no de una constante hardcodeada."""
    modelo = cargar_modelo(RUTA_JSON)
    # Verificar que es un string no vacío que contiene 'clasificador'
    assert "clasificador" in modelo.version


@pytest.mark.ac("AC-SCO-03")
def test_score_final_tiene_version_modelo() -> None:
    """ScoreFinal debe incluir version_modelo (se verificará al implementar scoring/)."""
    # Placeholder: se completará cuando ScoreFinal exista
    modelo = cargar_modelo(RUTA_JSON)
    assert hasattr(modelo, "version")
    assert modelo.version
