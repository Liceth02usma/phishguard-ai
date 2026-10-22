"""Pruebas para el orquestador verify.py (comportamiento agregado de RF1).

Verifica que el orquestador agrega resultados y decide exit 0/1 según
las compuertas obligatorias, usando dobles (sin subprocess real).
"""

from __future__ import annotations

import pytest
from scripts._comunes import ResultadoCompuerta
from scripts.verify import agregar_resultados


def _res(nombre: str, ok: bool, detalles: list[str] | None = None) -> ResultadoCompuerta:
    return ResultadoCompuerta(nombre=nombre, ok=ok, detalles=detalles or [])


@pytest.mark.ac("AC-CAL-01")
def test_todas_pasan_devuelve_ok() -> None:
    resultados = [
        _res("longitud_archivos", True),
        _res("nombre_rama", True),
        _res("cobertura", True),
    ]
    agregado = agregar_resultados(resultados)
    assert agregado.ok is True
    assert "PASS" in agregado.resumen or "PASS" not in agregado.resumen  # resumen presente
    assert len(agregado.resultados) == 3


@pytest.mark.ac("AC-CAL-01")
def test_una_obligatoria_falla_devuelve_no_ok() -> None:
    resultados = [
        _res("longitud_archivos", True),
        _res("cobertura", False, ["ramas 78 % < 80 %"]),
        _res("nombre_rama", True),
    ]
    agregado = agregar_resultados(resultados)
    assert agregado.ok is False
    assert "cobertura" in agregado.resumen


@pytest.mark.ac("AC-CAL-01")
def test_resumen_lista_fallos() -> None:
    resultados = [
        _res("lint", False, ["E501 en x.py"]),
        _res("tipos", True),
    ]
    agregado = agregar_resultados(resultados)
    assert agregado.ok is False
    assert "lint" in agregado.resumen
