"""Reintentos y cortacircuitos (spec 006, FR-003/FR-004, research D6).

`reintentar` reintenta 429/5xx con espera exponencial 1/2/4 s + jitter
inyectable y `Retry-After` respetado (segundos o fecha HTTP); un error de
transporte NO se reintenta (D6). `Cortacircuito` abre 60 s tras 5 fallos
consecutivos, sin estado de medio-abierto (FR-004); es propiedad de
`DependenciasVT` — sin globales de módulo (Art. II.5, determinismo).
"""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

from src.level2_agent.virustotal.modelos import (
    ESPERA_BASE_SEGUNDOS,
    FALLOS_CORTACIRCUITO,
    REINTENTOS_MAX,
    VENTANA_CORTACIRCUITO_SEGUNDOS,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from src.level2_agent.virustotal.puertos import Dormir, Jitter, Reloj, RespuestaVT


def _es_reintentable(estado: int) -> bool:
    """429 y 5xx son reintentables; 4xx restantes son terminales (FR-003)."""
    return estado == 429 or 500 <= estado <= 599


def _espera_retry_after(valor: str, ahora: datetime) -> float | None:
    """Retry-After en segundos o fecha HTTP → segundos desde `ahora` (FR-003).

    Valor ilegible → None (se usa la espera exponencial como respaldo).
    """
    texto = valor.strip()
    try:
        return max(0.0, float(texto))
    except ValueError:
        pass
    try:
        fecha = parsedate_to_datetime(texto)
    except (TypeError, ValueError):
        return None
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=UTC)
    return max(0.0, (fecha - ahora).total_seconds())


async def reintentar(
    accion: Callable[[], Awaitable[RespuestaVT]],
    *,
    reloj: Reloj,
    dormir: Dormir,
    jitter: Jitter,
) -> RespuestaVT | None:
    """Ejecuta `accion` reintentando 429/5xx hasta `REINTENTOS_MAX` (FR-003, D6).

    Espera exponencial `ESPERA_BASE_SEGUNDOS * 2^n` + jitter por intento; si la
    respuesta trae `Retry-After` (segundos o fecha HTTP) ese valor manda.
    Devuelve `None` si hubo error de transporte (sin reintento, fallo directo
    para el cortacircuitos — D6).
    """
    respuesta: RespuestaVT | None = None
    for intento in range(REINTENTOS_MAX + 1):
        try:
            respuesta = await accion()
        except Exception:  # cualquier error de transporte es fallo inmediato (D6)
            return None
        if not _es_reintentable(respuesta.status):
            return respuesta
        if intento == REINTENTOS_MAX:
            return respuesta
        espera = ESPERA_BASE_SEGUNDOS * (2**intento) + jitter()
        encabezado = respuesta.headers.get("retry-after")
        if encabezado is not None:
            personalizada = _espera_retry_after(encabezado, reloj())
            if personalizada is not None:
                espera = personalizada
        await dormir(espera)
    return respuesta


class Cortacircuito:
    """Cortacircuitos en proceso: 5 fallos → abierto 60 s (FR-004, sin medio-abierto).

    Una instancia por `DependenciasVT`: cada grupo de dependencias tiene el
    suyo (Estado en proceso con dataclass — data-model.md).
    """

    def __init__(self, reloj: Reloj) -> None:
        self._reloj = reloj
        self._fallos = 0
        self._abierto_desde: datetime | None = None

    @property
    def fallos(self) -> int:
        """Fallos consecutivos acumulados (útil para pruebas/observabilidad)."""
        return self._fallos

    def esta_abierto(self) -> bool:
        """True durante la ventana de 60 s; al vencer se cierra solo (FR-004)."""
        if self._abierto_desde is None:
            return False
        transcurrido = (self._reloj() - self._abierto_desde).total_seconds()
        if transcurrido >= VENTANA_CORTACIRCUITO_SEGUNDOS:
            self._abierto_desde = None
            self._fallos = 0
            return False
        return True

    def registrar_fallo(self) -> None:
        """Suma un fallo; al llegar a 5 abre la ventana de 60 s (FR-004)."""
        self._fallos += 1
        if self._fallos >= FALLOS_CORTACIRCUITO:
            self._abierto_desde = self._reloj()

    def registrar_exito(self) -> None:
        """Un veredicto concluyente (200/404) reinicia el contador (FR-004)."""
        self._fallos = 0
        self._abierto_desde = None
