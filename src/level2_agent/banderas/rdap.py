"""Adapter RDAP para la edad del dominio: cliente, cache y banderas (spec 003, FR-006).

``ClienteRDAP`` es la interfaz (Protocol). ``RequestsRDAP`` es la implementacion real
que jamas lanza excepcion (todo fallo se traduce en ``None`` -> banda conservadora
``DOMINIO_EDAD_DESCONOCIDA``). La cache de exitos vive 7 dias; los fallos se memoizan
dentro de la misma invocacion (decision D7).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

import requests

from .modelos import (
    DIAS_CACHE_RDAP,
    DIAS_DOMINIO_NUEVO,
    TIMEOUT_RDAP_SEGUNDOS,
    BanderaActivada,
    ContextoEvaluacion,
    EvaluadorBandera,
    dominio_de,
    fabricar_bandera,
    primer_valor,
)


class ClienteRDAP(Protocol):
    """Interfaz (Adapter) para obtener la fecha de registro; nunca lanza excepcion."""

    def registrar_evento(self, dominio: str) -> datetime | None:
        ...


def _parsear_fecha(cru: object) -> datetime | None:
    if not cru:
        return None
    try:
        fecha = datetime.fromisoformat(str(cru).replace("Z", "+00:00"))
    except ValueError:
        return None
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=UTC)
    return fecha


class RequestsRDAP:
    """Cliente RDAP real sobre HTTP; cualquier fallo se traduce en ``None``."""

    def registrar_evento(self, dominio: str) -> datetime | None:
        for plantilla in (
            "https://rdap.org/domain/{d}",
            "https://rdap.verisign.com/com/v1/domain/{d}",
        ):
            try:
                resp = requests.get(plantilla.format(d=dominio), timeout=TIMEOUT_RDAP_SEGUNDOS)
                if resp.status_code != 200:
                    continue
                eventos = resp.json().get("events", [])
                for evento in eventos:
                    if evento.get("eventAction") == "registration":
                        return _parsear_fecha(evento.get("eventDate"))
                return None  # 200 pero sin evento de registro
            except Exception:
                continue
        return None


class CacheRDAP:
    """Cache en memoria de exitos RDAP con TTL de 7 dias (FR-006)."""

    def __init__(self) -> None:
        self._entradas: dict[str, tuple[datetime, datetime]] = {}

    def obtener(self, dominio: str, ahora: datetime) -> datetime | None:
        golpe = self._entradas.get(dominio)
        if golpe is None:
            return None
        fecha, expira = golpe
        if ahora >= expira:
            del self._entradas[dominio]
            return None
        return fecha

    def guardar(self, dominio: str, fecha: datetime, ahora: datetime) -> None:
        self._entradas[dominio] = (fecha, ahora + timedelta(days=DIAS_CACHE_RDAP))


def crear_consultor_rdap(
    cliente: ClienteRDAP, cache: CacheRDAP, ahora: datetime
) -> Callable[[str], datetime | None]:
    """Cierra sobre cliente+cache+reloj: exitos 7 dias, fallos memoizados por invocacion."""
    fallos: set[str] = set()

    def consultor(dominio: str) -> datetime | None:
        if dominio in fallos:
            return None
        golpe = cache.obtener(dominio, ahora)
        if golpe is not None:
            return golpe
        fecha = cliente.registrar_evento(dominio)
        if fecha is not None:
            cache.guardar(dominio, fecha, ahora)
        else:
            fallos.add(dominio)
        return fecha

    return consultor


def _dominio_remitente(ctx: ContextoEvaluacion) -> str | None:
    valor = primer_valor(ctx.correo, "from")
    return dominio_de(valor) if valor is not None else None


class DominioNuevo:
    """El dominio se registro hace menos de 30 dias (catalogo 5.1, FR-006)."""

    codigo = "DOMINIO_NUEVO"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        dominio = _dominio_remitente(ctx)
        if dominio is None:
            return None
        fecha = ctx.consultar_fecha_registro(dominio)
        if fecha is None:
            return None
        edad = (ctx.ahora - fecha).total_seconds() / 86400
        if 0 <= edad < DIAS_DOMINIO_NUEVO:
            return fabricar_bandera(
                self.codigo, f"Dominio '{dominio}' registrado hace {int(edad)} dias"
            )
        return None


class DominioEdadDesconocida:
    """RDAP no devolvio fecha de registro -> edad desconocida (informativa, 0 puntos)."""

    codigo = "DOMINIO_EDAD_DESCONOCIDA"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        dominio = _dominio_remitente(ctx)
        if dominio is None:
            return None
        if ctx.consultar_fecha_registro(dominio) is not None:
            return None
        return fabricar_bandera(
            self.codigo, f"RDAP no devolvio fecha de registro de '{dominio}'"
        )


REGISTRO_RDAP: list[EvaluadorBandera] = [DominioNuevo(), DominioEdadDesconocida()]
