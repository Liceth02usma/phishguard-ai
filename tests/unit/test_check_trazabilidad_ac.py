"""Pruebas para la compuerta de trazabilidad AC→prueba (AC-CAL-05).

Un criterio de aceptación definido en la spec sin prueba marcada aparece
en el informe.
"""

from __future__ import annotations

import pytest
from scripts.check_trazabilidad_ac import (
    evaluar_trazabilidad,
    extraer_acs_de_pruebas,
    extraer_acs_de_spec,
)

SPEC_EJEMPLO = """
## Acceptance Scenarios

1. **AC-CAL-01**: un archivo de 501 líneas falla.
2. **AC-CAL-02**: los nombres válidos pasan.
3. **AC-CAL-03**: cobertura baja hace fallar.
4. **AC-CAL-04**: una clave hace fallar secretos.
5. **AC-CAL-05**: un AC sin prueba aparece en el informe.
6. **AC-CAL-06**: la CI ejecuta verify.
"""

PRUEBAS_CON_5_ACS = '''
import pytest

@pytest.mark.ac("AC-CAL-01")
def test_a():
    assert True

@pytest.mark.ac("AC-CAL-02")
def test_b():
    assert True

@pytest.mark.ac("AC-CAL-03")
def test_c():
    assert True

@pytest.mark.ac("AC-CAL-04")
def test_d():
    assert True

@pytest.mark.ac("AC-CAL-06")
def test_f():
    assert True
'''


@pytest.mark.ac("AC-CAL-05")
def test_extraer_acs_de_spec() -> None:
    acs = extraer_acs_de_spec(SPEC_EJEMPLO)
    assert acs == [
        "AC-CAL-01",
        "AC-CAL-02",
        "AC-CAL-03",
        "AC-CAL-04",
        "AC-CAL-05",
        "AC-CAL-06",
    ]


@pytest.mark.ac("AC-CAL-05")
def test_ac_sin_prueba_aparece_en_informe() -> None:
    """AC-CAL-05 no está en PRUEBAS_CON_5_ACS → debe aparecer como faltante."""
    acs_spec = extraer_acs_de_spec(SPEC_EJEMPLO)
    acs_pruebas = extraer_acs_de_pruebas(PRUEBAS_CON_5_ACS)
    resultado = evaluar_trazabilidad(acs_spec, acs_pruebas)
    assert resultado.ok is False
    assert "AC-CAL-05" in resultado.detalles


@pytest.mark.ac("AC-CAL-05")
def test_todos_con_prueba_pasa() -> None:
    acs_spec = ["AC-CAL-01", "AC-CAL-02"]
    acs_pruebas = {"AC-CAL-01", "AC-CAL-02"}
    resultado = evaluar_trazabilidad(acs_spec, acs_pruebas)
    assert resultado.ok is True
    assert resultado.detalles == []
