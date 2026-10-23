"""Pruebas unitarias de dominios: distancia, homoglifos y dominio organizacional.

Incluye propiedades con `hypothesis` sobre la distancia de edición (research D5/D6).
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from src.level2_agent.banderas.dominios import (
    distancia_edicion,
    dominio_organizacional,
    normalizar_dominio,
)


def test_distancia_valores_limite() -> None:
    assert distancia_edicion("paypal.com", "paypa1.com") == 1
    assert distancia_edicion("paypal.com", "paypai.com") == 1
    assert distancia_edicion("a.com", "a.com") == 0
    # empresa.com.co vs empresa.com: subcadena, distancia 3 (> umbral) -> no confunde
    assert distancia_edicion("empresa.com.co", "empresa.com") == 3


def test_dominio_organizacional_usa_psl() -> None:
    assert dominio_organizacional("sub.empresa.com.co") == "empresa.com.co"
    assert dominio_organizacional("mail.empresa.com") == "empresa.com"
    assert dominio_organizacional("empresa.com") == "empresa.com"


def test_normalizar_homoglifos() -> None:
    # "раypal.com" con er/a cirilicas -> "paypal.com"
    assert normalizar_dominio("раypal.com") == "paypal.com"


@settings(deadline=None)
@given(st.text(max_size=20), st.text(max_size=20))
def test_distancia_propiedades(a: str, b: str) -> None:
    d = distancia_edicion(a, b)
    assert d >= 0
    assert distancia_edicion(b, a) == d  # simetrica
    if a == b:
        assert d == 0
    assert d >= abs(len(a) - len(b))  # cota inferior por longitud
