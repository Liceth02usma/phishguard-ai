"""Familia de identidad: cabeceras de respuesta, nombre visible y remitente (spec 003)."""

from __future__ import annotations

from .modelos import (
    BanderaActivada,
    ContextoEvaluacion,
    EvaluadorBandera,
    dominio_de,
    fabricar_bandera,
    nombre_visible,
    primer_valor,
)


def _es_externo(dominio: str | None, ctx: ContextoEvaluacion) -> bool:
    """Un dominio es externo si no figura en ``dominios_propios``."""
    return dominio is not None and dominio not in ctx.config.dominios_propios


class ReplyToDistinto:
    """Reply-To en un dominio distinto al remitente (``From``)."""

    codigo = "REPLY_TO_DISTINTO"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        desde = primer_valor(ctx.correo, "from")
        reply = primer_valor(ctx.correo, "reply-to")
        if desde is None or reply is None:
            return None
        d_from, d_reply = dominio_de(desde), dominio_de(reply)
        if d_from and d_reply and d_from != d_reply:
            return fabricar_bandera(self.codigo, f"Reply-To '{d_reply}' != remitente '{d_from}'")
        return None


class ReturnPathDistinto:
    """Return-Path en un dominio distinto al remitente."""

    codigo = "RETURN_PATH_DISTINTO"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        desde = primer_valor(ctx.correo, "from")
        retorno = primer_valor(ctx.correo, "return-path")
        if desde is None or retorno is None:
            return None
        d_from, d_rp = dominio_de(desde), dominio_de(retorno)
        if d_from and d_rp and d_from != d_rp:
            return fabricar_bandera(self.codigo, f"Return-Path '{d_rp}' != remitente '{d_from}'")
        return None


class NombreSuplanta:
    """El nombre visible contiene una marca pero el dominio es externo."""

    codigo = "NOMBRE_SUPLANTA"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        desde = primer_valor(ctx.correo, "from")
        if desde is None:
            return None
        if not _es_externo(dominio_de(desde), ctx):
            return None
        visible = nombre_visible(desde)
        if not visible:
            return None
        visible_l = visible.lower()
        for marca in ctx.config.marcas_protegidas:
            etiqueta = marca.split(".", 1)[0].lower()
            if etiqueta and etiqueta in visible_l:
                return fabricar_bandera(
                    self.codigo, f"Nombre '{visible}' contiene la marca '{etiqueta}'"
                )
        return None


class MessageIdDistinto:
    """Message-ID con un dominio distinto al remitente (y no es proveedor de envio)."""

    codigo = "MESSAGE_ID_DISTINTO"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        desde = primer_valor(ctx.correo, "from")
        msg_id = primer_valor(ctx.correo, "message-id")
        if desde is None or msg_id is None:
            return None
        d_from, d_msg = dominio_de(desde), dominio_de(msg_id)
        if d_from and d_msg and d_from != d_msg:
            if d_msg in ctx.config.proveedores_envio:
                return None  # Message-ID legitimo de un proveedor configurado
            return fabricar_bandera(self.codigo, f"Message-ID '{d_msg}' != remitente '{d_from}'")
        return None


class RemitenteExternoComoInterno:
    """Remitente externo que usa terminos que aparentan ser internos (texto/asunto)."""

    codigo = "REMITENTE_EXTERNO_COMO_INTERNO"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        desde = primer_valor(ctx.correo, "from")
        if desde is None:
            return None
        if not _es_externo(dominio_de(desde), ctx):
            return None
        texto = f"{ctx.correo.subject} {ctx.correo.texto_limpio}".lower()
        for termino in ctx.config.terminos_internos:
            if termino and termino in texto:
                return fabricar_bandera(
                    self.codigo, f"Remitente externo usa el termino interno '{termino}'"
                )
        return None


REGISTRO_IDENTIDAD: list[EvaluadorBandera] = [
    ReplyToDistinto(),
    ReturnPathDistinto(),
    NombreSuplanta(),
    MessageIdDistinto(),
    RemitenteExternoComoInterno(),
]
