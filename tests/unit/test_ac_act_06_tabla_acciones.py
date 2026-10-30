"""AC-ACT-06: cada veredicto de la tabla produce exactamente las acciones indicadas."""

from __future__ import annotations

from src.level2_agent.acciones.modelos import Accion
from src.level2_agent.acciones.tabla import resolver_acciones


def test_tabla_malicioso() -> None:
    """malicioso → [ETIQUETAR_PHISHING, ARCHIVAR, CREAR_TICKET]."""
    acciones = resolver_acciones("malicioso")
    assert acciones == [Accion.ETIQUETAR_PHISHING, Accion.ARCHIVAR, Accion.CREAR_TICKET]


def test_tabla_sospechoso() -> None:
    """sospechoso → [ETIQUETAR_REVISAR, CREAR_TICKET_BAJA]."""
    acciones = resolver_acciones("sospechoso")
    assert acciones == [Accion.ETIQUETAR_REVISAR, Accion.CREAR_TICKET_BAJA]


def test_tabla_revision_manual() -> None:
    """revision_manual → [ETIQUETAR_REVISAR, CREAR_TICKET_BAJA]."""
    acciones = resolver_acciones("revision_manual")
    assert acciones == [Accion.ETIQUETAR_REVISAR, Accion.CREAR_TICKET_BAJA]


def test_tabla_sin_indicadores() -> None:
    """sin_indicadores → [MARCAR_LEIDO]."""
    acciones = resolver_acciones("sin_indicadores")
    assert acciones == [Accion.MARCAR_LEIDO]
