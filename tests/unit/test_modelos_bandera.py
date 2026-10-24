"""Pruebas del modelo BanderaActivada: detalle sin PII (Art. V.4, T006/T036)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.modelos import BanderaActivada
from src.level2_agent.banderas.motor import evaluar_banderas

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

# Direccion completa tipo correo; los dominios sueltos NO la activan.
_RE_CORREO_COMPLETO = r"[^\s@<>\"']+@[^\s@<>\"']+\.[a-z]{2,}"


def test_detalle_rechaza_direccion_completa() -> None:
    """Un detalle con direccion de correo completa viola Art. V.4 (fail-fast)."""
    with pytest.raises(ValidationError):
        BanderaActivada(
            codigo="DOMINIO_PARECIDO",
            severidad="alta",
            puntos=20,
            detalle="remitente cliente@paypa1.com suplanta a paypal.com",
        )


def test_detalle_acepta_dominios_y_evidencias() -> None:
    """Los dominios sueltos y las evidencias sin direccion son validos."""
    bandera = BanderaActivada(
        codigo="DOMINIO_PARECIDO",
        severidad="alta",
        puntos=20,
        detalle="dominio paypa1.com a distancia 1 de la marca paypal.com",
    )
    assert "paypa1.com" in bandera.detalle


def test_detalles_producidos_no_contienen_pii(
    construir_correo: Any, rdap_nulo: Any
) -> None:
    """Ningun detalle producido por un correo rico contiene una direccion completa."""
    import re

    config = ConfigBanderas(
        authserv_id="mio.com",
        marcas_protegidas=["paypal.com"],
        terminos_internos=["ayuda interna"],
    )
    correo = construir_correo(
        cabeceras=[
            ("From", "'PayPal' <cliente@paypa1.com>"),
            ("Reply-To", "captura@gmail.com"),
            ("Return-Path", "<bounce@otro.net>"),
            ("Message-ID", "<m@otro.net>"),
        ],
        asunto="Revisa la ayuda interna",
        texto_limpio="Consulta la ayuda interna de tu cuenta",
    )
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    assert r.banderas, "el correo debia producir banderas"
    for banda in r.banderas:
        assert re.search(_RE_CORREO_COMPLETO, banda.detalle) is None, (
            f"{banda.codigo} expuso PII en su detalle: {banda.detalle!r}"
        )
