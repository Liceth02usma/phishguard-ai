"""Limitador de tasa por proceso (spec 006, FR-002, research D5).

Cubeta de fichas por ventana de 60 s (`VT_RPM`, default 4/min público de
M06.1). Reloj y dormir inyectados: en pruebas NUNCA se duerme real — el
dormir falso avanza el reloj falso (Art. II.5). El contador diario (500/día)
vive en `RepositorioContadorVT`, no aquí; `cliente.py` lo orquesta (D5b).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.level2_agent.virustotal.modelos import VENTANA_RPM_SEGUNDOS

if TYPE_CHECKING:
    from src.level2_agent.virustotal.puertos import Dormir, Reloj


class Limitador:
    """Cubeta de fichas por minuto; propiedad de `DependenciasVT` (Art. III.2)."""

    def __init__(self, *, reloj: Reloj, dormir: Dormir) -> None:
        self._reloj = reloj
        self._dormir = dormir
        self._ventana_iniciada: datetime | None = None
        self._usadas = 0

    async def esperar_ficha(self, rpm: int) -> None:
        """Espera hasta disponer de una ficha de la ventana de minuto (FR-002).

        Con `rpm` fichas consumidas en la ventana, duerme el tiempo restante
        hasta los 60 s (dormir inyectado; en pruebas avanza el reloj falso).
        Una ventana vencida se repone sin esperar (límite 59 s vs 60 s).
        """
        ahora = self._reloj()
        ventana = self._ventana_iniciada
        if ventana is None or (ahora - ventana).total_seconds() >= VENTANA_RPM_SEGUNDOS:
            self._ventana_iniciada = ahora
            self._usadas = 0
            ventana = ahora
        if self._usadas >= rpm:
            restante = VENTANA_RPM_SEGUNDOS - (ahora - ventana).total_seconds()
            await self._dormir(max(0.0, restante))
            self._ventana_iniciada = self._reloj()
            self._usadas = 0
        self._usadas += 1
