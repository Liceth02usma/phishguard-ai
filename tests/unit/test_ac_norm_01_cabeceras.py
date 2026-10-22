"""AC-NORM-01: un correo con 2 cabeceras `Received` conserva ambas y en orden."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from src.level2_agent.normalizacion import normalizar_desde_eml


@pytest.mark.ac("AC-NORM-01")
def test_dos_received_conservadas_en_orden(fabrica_eml: Callable[..., bytes]) -> None:
    """Las dos cabeceras `Received` aparecen, en orden, en `cabeceras`."""
    eml = fabrica_eml(received=("by primer-servidor;1", "by segundo-servidor;2"))
    resultado = normalizar_desde_eml(eml)

    recibidas = [c.valor for c in resultado.cabeceras if c.nombre.lower() == "received"]
    assert len(recibidas) == 2
    assert recibidas[0].startswith("by primer-servidor")
    assert recibidas[1].startswith("by segundo-servidor")


@pytest.mark.ac("AC-NORM-01")
def test_orden_fisico_conservado(fabrica_eml: Callable[..., bytes]) -> None:
    """El orden de `cabeceras` respeta el orden físico del mensaje."""
    eml = fabrica_eml(
        received=("by a;1",),
        cabeceras_extra=(("X-Custom", "valor-x"),),
    )
    resultado = normalizar_desde_eml(eml)

    nombres = [c.nombre.lower() for c in resultado.cabeceras]
    assert nombres.index("from") < nombres.index("received")
    assert "x-custom" in nombres


@pytest.mark.ac("AC-NORM-01")
def test_origen_api_para_eml(fabrica_eml: Callable[..., bytes]) -> None:
    """Un `.eml` se marca con `origen="api"` (partición de equivalencia de entrada)."""
    eml = fabrica_eml()
    resultado = normalizar_desde_eml(eml)
    assert resultado.origen == "api"
