"""AC-SCO-06: coincidencia por palabra completa (FR-004).

"urgente" NO coincide en "insurgente", SÍ en "urgente," (puntuación pegada),
mayúsculas y acentos.
"""

from __future__ import annotations

import pytest
from src.level3_logic.genetic_logic import _contiene_alguna


@pytest.mark.ac("AC-SCO-06")
def test_urgente_no_en_insurgente() -> None:
    """'urgente' no debe coincidir dentro de 'insurgente'."""
    # Con la implementación actual (substring), esto FALLA —
    # se corregirá con contiene_palabra_completa (T015).
    resultado = _contiene_alguna(["urgente"], "insurgente")
    # Después de T015, esto será False
    # Por ahora documentamos el comportamiento actual
    assert resultado is False, "'urgente' no debe coincidir en 'insurgente'"


@pytest.mark.ac("AC-SCO-06")
def test_urgente_si_con_puntuacion() -> None:
    """'urgente' SÍ coincide en 'urgente,' (puntuación pegada)."""
    resultado = _contiene_alguna(["urgente"], "urgente,")
    assert resultado is True


@pytest.mark.ac("AC-SCO-06")
def test_urgente_mayusculas() -> None:
    """'urgente' coincide en 'URGENTE' (case-insensitive)."""
    resultado = _contiene_alguna(["urgente"], "URGENTE")
    assert resultado is True


@pytest.mark.ac("AC-SCO-06")
def test_urgente_acentos() -> None:
    """'urgente' coincide en texto con acentos en otras palabras."""
    resultado = _contiene_alguna(["urgente"], "esto es urgente y necesario")
    assert resultado is True


@pytest.mark.ac("AC-SCO-06")
def test_banco_no_en_bancocracia() -> None:
    """'banco' no coincide en 'bancocracia'."""
    resultado = _contiene_alguna(["banco"], "bancocracia")
    assert resultado is False


@pytest.mark.ac("AC-SCO-06")
def test_banco_si_al_inicio() -> None:
    """'banco' coincide al inicio de oración."""
    resultado = _contiene_alguna(["banco"], "banco de la nación")
    assert resultado is True
