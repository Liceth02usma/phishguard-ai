"""Familia de autenticacion: parser RFC 8601 y banderas SPF/DKIM/DMARC (spec 003).

Solo se confia en el ``Authentication-Results`` cuyo ``authserv-id`` coincide con
``config.authserv_id`` (FR-001). Si no existe cabecera confiable, los estados
quedan en ``desconocido`` (nunca se infiere ``pass``, FR-003) y se activa
``AUTH_NO_EVALUABLE`` (decision D4).
"""

from __future__ import annotations

import re
from typing import cast

from src.level2_agent.models import Cabecera

from .configuracion import ConfigBanderas
from .modelos import (
    BanderaActivada,
    ContextoEvaluacion,
    EstadoAuth,
    EstadosAutenticacion,
    EvaluadorBandera,
    ResultadoAutenticacion,
    fabricar_bandera,
)

_METODOS = frozenset({"spf", "dkim", "dmarc"})
_RESULTADOS = frozenset(
    {"pass", "fail", "softfail", "neutral", "none", "permerror", "temperror"}
)
_RE_COMENTARIO = re.compile(r"\([^)]*\)")
_RE_PAR = re.compile(r"^([a-z0-9-]+)=([a-z0-9-]+)$")


def _authserv_de(segmento: str) -> str:
    """Extrae el ``authserv-id`` (token inicial hasta el primer ``;``, sin comentarios)."""
    antes_del_punto_y_coma = segmento.split(";", 1)[0]
    limpio = _RE_COMENTARIO.sub("", antes_del_punto_y_coma).strip()
    if not limpio:
        return ""
    return limpio.split()[0].strip().lower().rstrip(".")


def _metodos_de(valor: str) -> dict[str, EstadoAuth]:
    """``{metodo: resultado}`` del Authentication-Results (separado por ``;``)."""
    segmentos = valor.split(";")
    metodos: dict[str, EstadoAuth] = {}
    for seg in segmentos[1:]:
        for token in seg.split():
            m = _RE_PAR.match(token.lower())
            if m and m.group(1) in _METODOS and m.group(2) in _RESULTADOS:
                # ya validado contra _RESULTADOS: el resultado es un EstadoAuth
                metodos.setdefault(m.group(1), cast(EstadoAuth, m.group(2)))
    return metodos


def _a_estado(metodos: dict[str, EstadoAuth], metodo: str) -> EstadoAuth:
    """Estado de ``metodo`` o ``desconocido`` si no viene evaluado (FR-003)."""
    est = metodos.get(metodo)
    return est if est is not None else "desconocido"


def calcular_autenticacion(
    config: ConfigBanderas, cabeceras: list[Cabecera]
) -> ResultadoAutenticacion:
    """Estados SPF/DKIM/DMARC tomando solo el ``Authentication-Results`` de confianza.

    El primero en orden fisico con ``authserv-id`` coincidente gana (FR-001).
    ``authserv_id`` vacio => ninguna cabecera es de confianza (conservador, D9).
    """
    objetivo = config.authserv_id.lower().rstrip(".")
    if objetivo:
        for c in cabeceras:
            if c.nombre.lower() != "authentication-results":
                continue
            authserv = _authserv_de(c.valor)
            if authserv and authserv == objetivo:
                metodos = _metodos_de(c.valor)
                estados = EstadosAutenticacion(
                    spf=_a_estado(metodos, "spf"),
                    dkim=_a_estado(metodos, "dkim"),
                    dmarc=_a_estado(metodos, "dmarc"),
                )
                return ResultadoAutenticacion(estados=estados, hay_confiable=True)
    return ResultadoAutenticacion(estados=EstadosAutenticacion(), hay_confiable=False)


class SpfFalla:
    """SPF evaluado como ``fail``/``softfail``."""

    codigo = "SPF_FALLA"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        est = ctx.autenticacion.estados.spf
        if est in ("fail", "softfail"):
            return fabricar_bandera(self.codigo, f"SPF evaluado como {est}")
        return None


class DkimFalla:
    """DKIM evaluado como ``fail``."""

    codigo = "DKIM_FALLA"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        if ctx.autenticacion.estados.dkim == "fail":
            return fabricar_bandera(self.codigo, "DKIM evaluado como fail")
        return None


class DmarcFalla:
    """DMARC evaluado como ``fail``."""

    codigo = "DMARC_FALLA"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        if ctx.autenticacion.estados.dmarc == "fail":
            return fabricar_bandera(self.codigo, "DMARC evaluado como fail")
        return None


class AuthNoEvaluable:
    """Sin ``Authentication-Results`` de confianza (no se evaluo la autenticacion)."""

    codigo = "AUTH_NO_EVALUABLE"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        if not ctx.autenticacion.hay_confiable:
            return fabricar_bandera(self.codigo, "Sin Authentication-Results de confianza")
        return None


REGISTRO_AUTENTICACION: list[EvaluadorBandera] = [
    SpfFalla(),
    DkimFalla(),
    DmarcFalla(),
    AuthNoEvaluable(),
]
