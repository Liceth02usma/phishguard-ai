"""Pruebas para la compuerta de cobertura (AC-CAL-03).

Valores límite: 79 % y 80 % respecto al umbral 80.
"""

from __future__ import annotations

import pytest
from scripts._comunes import COBERTURA_MIN
from scripts.verify import evaluar_cobertura


@pytest.mark.ac("AC-CAL-03")
def test_cobertura_78_porciento_falla() -> None:
    """78 % < 80 % → la compuerta falla."""
    resultado = evaluar_cobertura(78.0)
    assert resultado.ok is False
    assert "78" in resultado.detalles[0]


@pytest.mark.ac("AC-CAL-03")
def test_cobertura_80_porciento_pasa() -> None:
    """En el límite exacto (80 %) la compuerta pasa."""
    resultado = evaluar_cobertura(80.0)
    assert resultado.ok is True


@pytest.mark.ac("AC-CAL-03")
def test_cobertura_100_porciento_pasa() -> None:
    resultado = evaluar_cobertura(100.0)
    assert resultado.ok is True


def test_umbral_constante_es_80() -> None:
    assert COBERTURA_MIN == 80
