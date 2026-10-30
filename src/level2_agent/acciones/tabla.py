"""Tabla de mapeo veredicto→acciones (spec 010, M08, FR-001).

Datos puros — sin lógica condicional. Cada veredicto mapea a una
lista de acciones deterministas. La tabla es la única fuente de
verdad para qué acciones se ejecutan (Art. VI.2).
"""

from __future__ import annotations

from src.level2_agent.acciones.modelos import Accion, Veredicto

# --- Tabla de mapeo (FR-001, D3) ---

_TABLA: dict[Veredicto, list[Accion]] = {
    "malicioso": [
        Accion.ETIQUETAR_PHISHING,
        Accion.ARCHIVAR,
        Accion.CREAR_TICKET,
    ],
    "sospechoso": [
        Accion.ETIQUETAR_REVISAR,
        Accion.CREAR_TICKET_BAJA,
    ],
    "revision_manual": [
        Accion.ETIQUETAR_REVISAR,
        Accion.CREAR_TICKET_BAJA,
    ],
    "sin_indicadores": [
        Accion.MARCAR_LEIDO,
    ],
}


def resolver_acciones(veredicto: Veredicto) -> list[Accion]:
    """Retorna las acciones para el veredicto dado (FR-001).

    La tabla es datos puros — nunca inventa acciones.
    """
    return list(_TABLA[veredicto])  # copia para evitar mutación
