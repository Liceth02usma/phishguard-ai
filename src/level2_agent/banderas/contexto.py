"""Familia de contexto: cabeceras Received/Date y Reply-To gratuito (spec 003, M04b)."""

from __future__ import annotations

import ipaddress
import re
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

from .modelos import (
    ANIOS_FECHA_VIEJA,
    DIAS_FECHA_FUTURA,
    REDES_PRIVADAS,
    BanderaActivada,
    ContextoEvaluacion,
    EvaluadorBandera,
    dominio_de,
    fabricar_bandera,
    obtener_cabeceras,
    primer_valor,
)

_RE_IP_ENTRE_CORCHETES = re.compile(r"\[([^\]]+)\]")
_REDES = [ipaddress.ip_network(r) for r in REDES_PRIVADAS]


def _ip_de_recibido(valor: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    for bruto in _RE_IP_ENTRE_CORCHETES.findall(valor):
        try:
            return ipaddress.ip_address(bruto.strip())
        except ValueError:
            continue
    return None


def _es_privada(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(ip in red for red in _REDES)


def _fecha_de_recibido(valor: str) -> datetime | None:
    if ";" not in valor:
        return None
    cola = valor.rsplit(";", 1)[1].strip()
    try:
        return parsedate_to_datetime(cola)
    except (TypeError, ValueError):
        return None


class ReceivedInconsistente:
    """Primer salto con IP privada o timestamps de Received fuera de orden."""

    codigo = "RECEIVED_INCONSISTENTE"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        recibidos = obtener_cabeceras(ctx.correo, "received")
        if not recibidos:
            return None
        # Regla (b): el primer salto externo no debe ser una IP privada.
        ip0 = _ip_de_recibido(recibidos[0])
        if ip0 is not None and _es_privada(ip0):
            return fabricar_bandera(self.codigo, f"Primer salto con IP privada {ip0}")
        # Regla (a): los timestamps deben ser no crecientes (de arriba hacia abajo).
        fechas = [f for f in (_fecha_de_recibido(v) for v in recibidos) if f is not None]
        for i in range(len(fechas) - 1):
            if fechas[i + 1] > fechas[i]:
                return fabricar_bandera(self.codigo, "Timestamps de Received fuera de orden")
        return None


class FechaAnomala:
    """Fecha del correo mas de 24 h en el futuro o con mas de un anio (catalogo 5.1)."""

    codigo = "FECHA_ANOMALA"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        valor = primer_valor(ctx.correo, "date")
        if valor is None:
            return None
        try:
            fecha = parsedate_to_datetime(valor)
        except (TypeError, ValueError):
            return None
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=UTC)
        if fecha > ctx.ahora + timedelta(days=DIAS_FECHA_FUTURA):
            return fabricar_bandera(self.codigo, "Fecha del correo mas de 24 h en el futuro")
        if fecha < ctx.ahora - timedelta(days=365 * ANIOS_FECHA_VIEJA):
            return fabricar_bandera(
                self.codigo, "Fecha del correo con mas de un anio de antiguedad"
            )
        return None


class ReplyToGratuito:
    """Reply-To en dominio gratuito con remitente corporativo (no gratuito)."""

    codigo = "REPLY_TO_GRATUITO"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        desde = primer_valor(ctx.correo, "from")
        reply = primer_valor(ctx.correo, "reply-to")
        if desde is None or reply is None:
            return None
        d_from, d_reply = dominio_de(desde), dominio_de(reply)
        if d_from is None or d_reply is None:
            return None
        if d_from in ctx.config.dominios_gratuitos:
            return None  # el remitente ya es gratuito
        if d_reply in ctx.config.dominios_gratuitos:
            return fabricar_bandera(
                self.codigo, f"Reply-To gratuito '{d_reply}' con remitente '{d_from}'"
            )
        return None


REGISTRO_CONTEXTO: list[EvaluadorBandera] = [
    ReceivedInconsistente(),
    FechaAnomala(),
    ReplyToGratuito(),
]
