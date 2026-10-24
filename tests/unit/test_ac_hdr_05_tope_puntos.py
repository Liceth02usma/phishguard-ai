"""AC-HDR-05: la suma de puntos de las banderas de un correo nunca supera 60 (tope)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.modelos import (
    CATALOGO_BANDERAS,
    TOPE_PUNTOS_BANDERAS,
    BanderaActivada,
    fabricar_bandera,
)
from src.level2_agent.banderas.motor import calcular_puntos, evaluar_banderas

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _seis_desinueve() -> list[BanderaActivada]:
    """Banderas cuya suma sin tope da 61 (la mayor que se puede superar en 1)."""
    return [
        fabricar_bandera("DOMINIO_PARECIDO", "a"),  # 20
        fabricar_bandera("DMARC_FALLA", "b"),  # 15
        fabricar_bandera("DOMINIO_NUEVO", "c"),  # 15
        fabricar_bandera("SPF_FALLA", "d"),  # 10
        BanderaActivada(  # puntos sintéticos para alcanzar exactamente 61
            codigo="FECHA_ANOMALA", severidad="baja", puntos=1, detalle="e"
        ),
    ]


@pytest.mark.ac("AC-HDR-05")
def test_tope_en_valores_limite() -> None:
    banda_61 = _seis_desinueve()
    assert sum(b.puntos for b in banda_61) == 61
    assert calcular_puntos(banda_61) == TOPE_PUNTOS_BANDERAS == 60

    banda_60 = [fabricar_bandera(c, "x") for c in (
        "DOMINIO_PARECIDO", "DMARC_FALLA", "DOMINIO_NUEVO", "SPF_FALLA",
    )]
    assert sum(b.puntos for b in banda_60) == 60
    assert calcular_puntos(banda_60) == 60


@pytest.mark.ac("AC-HDR-05")
def test_integracion_puntos_nunca_superan_60(construir_correo: Any, rdap_nulo: Any) -> None:
    """Correo real que dispara varias banderas: puntos acotados y coherentes con el desglose."""
    config = ConfigBanderas(
        authserv_id="mio.com",
        marcas_protegidas=["paypal.com"],
        terminos_internos=["ayuda interna"],
    )
    correo = construir_correo(
        cabeceras=[
            ("From", "'PayPal' <cliente@paypa1.com>"),
            ("Reply-To", "captura@gmail.com"),
            ("Message-ID", "<m@otro.net>"),
        ],
        asunto="Revisa la ayuda interna",
        texto_limpio="Consulta la ayuda interna de tu cuenta",
    )
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    assert len(r.banderas) >= 3  # varias banderas activas
    assert r.puntos_totales <= TOPE_PUNTOS_BANDERAS
    assert r.puntos_totales == calcular_puntos(r.banderas)


@pytest.mark.ac("AC-HDR-05")
@given(codigos=st.lists(st.sampled_from(sorted(CATALOGO_BANDERAS)), max_size=16))
def test_propiedad_tope_sobre_subconjuntos(codigos: list[str]) -> None:
    """Cualquier subconjunto del catalogo cumple puntos_totales == min(suma, 60) (data-model)."""
    banderas = [fabricar_bandera(c, "x") for c in codigos]
    assert calcular_puntos(banderas) == min(
        sum(b.puntos for b in banderas), TOPE_PUNTOS_BANDERAS
    )
    assert 0 <= calcular_puntos(banderas) <= TOPE_PUNTOS_BANDERAS
