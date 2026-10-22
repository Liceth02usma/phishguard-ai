"""AC-NORM-06: entradas degradadas no lanzan y se marcan para revisión manual."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from src.level2_agent.normalizacion import (
    BANDERA_ENTRADA_DEGRADADA,
    normalizar_desde_eml,
)


@pytest.mark.ac("AC-NORM-06")
def test_entrada_vacia_no_lanza() -> None:
    """Una entrada vacía no lanza y queda degradada + revisión manual."""
    resultado = normalizar_desde_eml(b"")
    assert BANDERA_ENTRADA_DEGRADADA in resultado.banderas
    assert resultado.revision_manual is True


@pytest.mark.ac("AC-NORM-06")
def test_cuerpo_vacio_no_lanza() -> None:
    """Un correo con cabeceras pero cuerpo vacío no lanza y queda degradado."""
    eml = b"From: a@b.com\r\nTo: c@d.com\r\nSubject: x\r\n\r\n"
    resultado = normalizar_desde_eml(eml)
    assert BANDERA_ENTRADA_DEGRADADA in resultado.banderas
    assert resultado.revision_manual is True


@pytest.mark.ac("AC-NORM-06")
def test_sin_cabeceras_no_lanza() -> None:
    """Un correo sin cabeceras identificables no lanza y queda degradado."""
    eml = b"cuerpo suelto sin cabeceras\r\n"
    resultado = normalizar_desde_eml(eml)
    assert BANDERA_ENTRADA_DEGRADADA in resultado.banderas
    assert resultado.revision_manual is True


@pytest.mark.ac("AC-NORM-06")
def test_codificacion_invalida_no_lanza() -> None:
    """Una parte con charset inexistente no lanza excepción no controlada."""
    eml = (
        b"From: a@b.com\r\nTo: c@d.com\r\nSubject: x\r\n"
        b"Content-Type: text/plain; charset=x-noexiste-abc\r\n\r\n"
        b"contenido con bytes \xff\xfe"
    )
    resultado = normalizar_desde_eml(eml)  # no debe lanzar
    assert BANDERA_ENTRADA_DEGRADADA in resultado.banderas
    assert resultado.revision_manual is True


@pytest.mark.ac("AC-NORM-06")
def test_bytes_basura_no_lanza() -> None:
    """Bytes que no son un correo no lanzan excepción no controlada."""
    resultado = normalizar_desde_eml(b"\x00\x01\x02\xff\xfe basura")
    assert resultado.revision_manual is True


@pytest.mark.ac("AC-NORM-06")
def test_correo_valido_no_degradado(fabrica_eml: Callable[..., bytes]) -> None:
    """Un correo bien formado NO queda degradado (par negativo de la partición)."""
    eml = fabrica_eml(texto="cuerpo normal")
    resultado = normalizar_desde_eml(eml)
    assert BANDERA_ENTRADA_DEGRADADA not in resultado.banderas
    assert resultado.revision_manual is False
