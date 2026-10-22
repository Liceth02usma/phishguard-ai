"""Pruebas para la compuerta de longitud de archivos (AC-CAL-01).

Valores límite: ' 500 líneas pasa, 501 falla.
"""

from __future__ import annotations

import pytest
from scripts._comunes import LIMITE_LINEAS
from scripts.check_longitud_archivos import evaluar_longitud


@pytest.mark.ac("AC-CAL-01")
def test_archivo_500_lineas_pasa(tmp_py_file: object) -> None:
    """En el límite exacto (500 líneas) la compuerta pasa."""
    ruta = tmp_py_file(500)  # type: ignore[operator]
    resultado = evaluar_longitud([ruta])
    assert resultado.ok is True
    assert resultado.detalles == []


@pytest.mark.ac("AC-CAL-01")
def test_archivo_501_lineas_falla(tmp_py_file: object) -> None:
    """Un archivo por encima del límite (501) hace fallar la compuerta."""
    ruta = tmp_py_file(501)  # type: ignore[operator]
    resultado = evaluar_longitud([ruta])
    assert resultado.ok is False
    assert len(resultado.detalles) == 1
    assert "501" in resultado.detalles[0]


@pytest.mark.ac("AC-CAL-01")
def test_varios_archivos_lista_todos_los_infractores(tmp_py_file: object) -> None:
    """Si hay varios infractores, todos aparecen en detalles."""
    ok = tmp_py_file(100, "ok.py")  # type: ignore[operator]
    mal1 = tmp_py_file(600, "mal1.py")  # type: ignore[operator]
    mal2 = tmp_py_file(502, "mal2.py")  # type: ignore[operator]
    resultado = evaluar_longitud([ok, mal1, mal2])
    assert resultado.ok is False
    assert len(resultado.detalles) == 2


def test_limite_constante_es_500() -> None:
    """El umbral vive como constante (Art. III.6)."""
    assert LIMITE_LINEAS == 500
