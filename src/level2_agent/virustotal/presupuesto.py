"""Presupuesto de consultas externas por correo (spec 006, FR-006, research D5).

El wiring por correo (specs 007/008) crea UN presupuesto con
`presupuesto_nuevo` y lo comparte entre las `consultar_*` del mismo correo:
eso es lo que garantiza FR-006 (máximo `VT_MAX_POR_CORREO`, default 10).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.level2_agent.virustotal.configuracion import ConfigVT
from src.level2_agent.virustotal.modelos import MAX_CONSULTAS_POR_CORREO


@dataclass
class Presupuesto:
    """Contador mutable de consultas restantes para un correo (FR-006, G8)."""

    restantes: int = MAX_CONSULTAS_POR_CORREO

    @property
    def agotado(self) -> bool:
        """True cuando ya no quedan consultas por consumir."""
        return self.restantes <= 0

    def usar(self) -> bool:
        """Consume 1 si queda; False estable al agotarse (no baja de 0)."""
        if self.restantes <= 0:
            return False
        self.restantes -= 1
        return True


def presupuesto_nuevo(config: ConfigVT | None = None) -> Presupuesto:
    """Presupuesto con `VT_MAX_POR_CORREO` (default 10) de la configuración (FR-006)."""
    cfg = config if config is not None else ConfigVT()
    return Presupuesto(restantes=cfg.max_por_correo)
