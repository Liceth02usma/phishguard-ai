"""AC-HDR-01: cada bandera del catálogo 5.1 tiene un correo que la activa y otro que no.

Recorre los 16 códigos con su par (positivo, negativo) y añade un correo canónico
con el conjunto exacto de banderas esperadas y sus puntos (test independiente).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any

import pytest
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.modelos import CATALOGO_BANDERAS, TOPE_PUNTOS_BANDERAS
from src.level2_agent.banderas.motor import evaluar_banderas
from src.level2_agent.banderas.rdap import reiniciar_cache_proceso

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_AUTH = "mio.com"
_AR_OK = ("Authentication-Results", f"{_AUTH}; spf=pass dkim=pass dmarc=pass")
_AR_SPF_FAIL = ("Authentication-Results", f"{_AUTH}; spf=fail dkim=pass dmarc=pass")
_AR_DKIM_FAIL = ("Authentication-Results", f"{_AUTH}; dkim=fail")
_AR_DMARC_FAIL = ("Authentication-Results", f"{_AUTH}; dmarc=fail")

# rdap: "nulo" -> double caido; datetime -> fecha de registro fija; str -> sin consultar
Fecha = Any

ESCENARIOS: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "SPF_FALLA": (
        {"cabeceras": [("From", "a@empresa.com"), _AR_SPF_FAIL]},
        {"cabeceras": [("From", "a@empresa.com"), _AR_OK]},
    ),
    "DKIM_FALLA": (
        {"cabeceras": [("From", "a@empresa.com"), _AR_DKIM_FAIL]},
        {"cabeceras": [("From", "a@empresa.com"), _AR_OK]},
    ),
    "DMARC_FALLA": (
        {"cabeceras": [("From", "a@empresa.com"), _AR_DMARC_FAIL]},
        {"cabeceras": [("From", "a@empresa.com"), _AR_OK]},
    ),
    "AUTH_NO_EVALUABLE": (
        {"cabeceras": [("From", "a@empresa.com")]},  # sin AR
        {"cabeceras": [("From", "a@empresa.com"), _AR_OK]},
    ),
    "REPLY_TO_DISTINTO": (
        {"cabeceras": [("From", "a@empresa.com"), ("Reply-To", "b@otro.com")]},
        {"cabeceras": [("From", "a@empresa.com"), ("Reply-To", "b@empresa.com")]},
    ),
    "RETURN_PATH_DISTINTO": (
        {"cabeceras": [("From", "a@empresa.com"), ("Return-Path", "<b@otro.com>")]},
        {"cabeceras": [("From", "a@empresa.com"), ("Return-Path", "<b@empresa.com>")]},
    ),
    "NOMBRE_SUPLANTA": (
        {  # nombre con marca + dominio externo -> suplanta
            "cabeceras": [("From", "'PayPal Soporte' <cli@externo.net>")],
            "config_extra": {"marcas_protegidas": ["paypal.com"]},
        },
        {  # mismo nombre pero dominio propio -> no es suplantación externa
            "cabeceras": [("From", "'PayPal Soporte' <ana@empresa.com>")],
            "config_extra": {
                "marcas_protegidas": ["paypal.com"],
                "dominios_propios": ["empresa.com"],
            },
        },
    ),
    "DOMINIO_PARECIDO": (
        {
            "cabeceras": [("From", "cli@paypa1.com")],
            "config_extra": {"marcas_protegidas": ["paypal.com"]},
        },
        {
            "cabeceras": [("From", "cli@empresa.com")],
            "config_extra": {"marcas_protegidas": ["paypal.com"]},
        },
    ),
    "DOMINIO_PUNYCODE": (
        {"cabeceras": [("From", "cli@xn--pypal-4ve.com")]},
        {"cabeceras": [("From", "cli@paypal.com")]},
    ),
    "MESSAGE_ID_DISTINTO": (
        {"cabeceras": [("From", "a@empresa.com"), ("Message-ID", "<m@otro.net>")]},
        {"cabeceras": [("From", "a@empresa.com"), ("Message-ID", "<m@empresa.com>")]},
    ),
    "RECEIVED_INCONSISTENTE": (
        {  # primer salto con IP privada
            "cabeceras": [
                ("From", "a@empresa.com"),
                ("Received", "from lan [192.168.1.10] by mx; Thu, 01 Jan 2026 11:59:00 +0000"),
            ]
        },
        {  # primer salto con IP publica
            "cabeceras": [
                ("From", "a@empresa.com"),
                ("Received", "from mx [203.0.113.10] by mx; Thu, 01 Jan 2026 11:59:00 +0000"),
            ]
        },
    ),
    "FECHA_ANOMALA": (
        {  # 2 dias en el futuro (> 24 h)
            "cabeceras": [("From", "a@empresa.com"), ("Date", "Thu, 03 Jan 2026 12:00:00 +0000")],
        },
        {  # 1 h en el futuro (< 24 h)
            "cabeceras": [("From", "a@empresa.com"), ("Date", "Thu, 01 Jan 2026 13:00:00 +0000")],
        },
    ),
    "REPLY_TO_GRATUITO": (
        {"cabeceras": [("From", "a@empresa.com"), ("Reply-To", "b@gmail.com")]},
        {"cabeceras": [("From", "a@empresa.com"), ("Reply-To", "b@empresa.com")]},
    ),
    "REMITENTE_EXTERNO_COMO_INTERNO": (
        {
            "cabeceras": [("From", "cli@externo.net")],
            "texto": "Escribe a la ayuda interna de tu cuenta",
            "config_extra": {"terminos_internos": ["ayuda interna"]},
        },
        {
            "cabeceras": [("From", "cli@externo.net")],
            "texto": "Oferta normal de temporada",
            "config_extra": {"terminos_internos": ["ayuda interna"]},
        },
    ),
    "DOMINIO_NUEVO": (
        {"cabeceras": [("From", "a@empresa.com")], "rdap": AHORA - timedelta(days=10)},
        {"cabeceras": [("From", "a@empresa.com")], "rdap": AHORA - timedelta(days=40)},
    ),
    "DOMINIO_EDAD_DESCONOCIDA": (
        {"cabeceras": [("From", "a@empresa.com")], "rdap": "nulo"},
        {"cabeceras": [("From", "a@empresa.com")], "rdap": AHORA - timedelta(days=40)},
    ),
}


def _eval(escenario: dict[str, Any], construir_correo: Any, rdap_nulo: Any, rdap_fijo: Any) -> Any:
    config = ConfigBanderas(authserv_id=_AUTH, **escenario.get("config_extra", {}))
    correo = construir_correo(
        cabeceras=escenario["cabeceras"],
        asunto=escenario.get("asunto", ""),
        texto_limpio=escenario.get("texto", ""),
    )
    rdap = escenario.get("rdap", "nulo")
    cliente = rdap_fijo(rdap) if isinstance(rdap, datetime) else rdap_nulo
    return evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=cliente)


@pytest.mark.ac("AC-HDR-01")
@pytest.mark.parametrize("codigo", sorted(ESCENARIOS))
def test_par_positivo_negativo(
    codigo: str, construir_correo: Any, rdap_nulo: Any, rdap_fijo: Any
) -> None:
    assert codigo in CATALOGO_BANDERAS  # el par existe en el catálogo
    pos, neg = ESCENARIOS[codigo]
    r_pos = _eval(pos, construir_correo, rdap_nulo, rdap_fijo)
    reiniciar_cache_proceso()  # el par negativo no hereda la fecha cacheada
    r_neg = _eval(neg, construir_correo, rdap_nulo, rdap_fijo)
    assert codigo in {b.codigo for b in r_pos.banderas}, f"{codigo} debia activarse"
    assert codigo not in {b.codigo for b in r_neg.banderas}, f"{codigo} debia permanecer inactiva"


@pytest.mark.ac("AC-HDR-01")
def test_correo_canonico_conjunto_exacto_y_puntos(construir_correo: Any, rdap_nulo: Any) -> None:
    config = ConfigBanderas(authserv_id=_AUTH, marcas_protegidas=["paypal.com"])
    correo = construir_correo(
        cabeceras=[
            ("From", "'PayPal' <cliente@paypa1.com>"),
            ("Reply-To", "captura@gmail.com"),
            ("Authentication-Results", "externo.net; spf=pass"),
        ],
        asunto="Revisa tu cuenta",
    )
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    codigos = {b.codigo for b in r.banderas}
    assert codigos == {
        "DOMINIO_PARECIDO",  # paypa1 ~ paypal (20)
        "NOMBRE_SUPLANTA",  # "PayPal" en nombre + dominio externo (15)
        "REPLY_TO_DISTINTO",  # gmail.com != paypa1.com (10)
        "REPLY_TO_GRATUITO",  # Reply-To gratuito con From no gratuito (10)
        "AUTH_NO_EVALUABLE",  # AR de externo, ignorado (5)
        "DOMINIO_EDAD_DESCONOCIDA",  # RDAP caido (0)
    }
    assert r.puntos_totales == sum(CATALOGO_BANDERAS[c][1] for c in codigos) == TOPE_PUNTOS_BANDERAS


@pytest.mark.ac("AC-HDR-01")
@pytest.mark.parametrize(
    ("delta", "esperada"),
    [
        (timedelta(hours=23), False),  # 23 h futuras < 24 h -> no anomala
        (timedelta(hours=25), True),  # 25 h futuras > 24 h -> anomala
        (timedelta(days=-364), False),  # 364 dias pasados < 1 anio -> no anomala
        (timedelta(days=-366), True),  # 366 dias pasados > 1 anio -> anomala
    ],
)
def test_fecha_anomala_valores_limite(
    delta: timedelta, esperada: bool, construir_correo: Any, rdap_nulo: Any
) -> None:
    """research D10.1: los bordes exactos de FECHA_ANOMALA (23/25 h, 364/366 días)."""
    reiniciar_cache_proceso()
    futuro = delta > timedelta(0)
    fecha = (AHORA + delta) if futuro else (AHORA - abs(delta))
    config = ConfigBanderas(authserv_id=_AUTH)
    correo = construir_correo(
        cabeceras=[("From", "a@empresa.com"), ("Date", format_datetime(fecha))]
    )
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    activada = "FECHA_ANOMALA" in {b.codigo for b in r.banderas}
    assert activada is esperada, f"delta={delta} debia dar FECHA_ANOMALA={esperada}"
