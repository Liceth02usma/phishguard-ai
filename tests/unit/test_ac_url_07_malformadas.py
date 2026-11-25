"""AC-URL-07: entradas malformadas, vacías o gigantes no lanzan excepción.

Propiedad con `hypothesis` (research D10.4): cualquier cadena arbitraria
pasa por `analizar_urls` sin excepción no controlada (invariante I6).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.level2_agent.analisis_urls import analizar_urls

from dobles_red import deps_de_prueba


@pytest.mark.ac("AC-URL-07")
def test_correo_vacio_no_lanza(fabrica_email_urls: Callable[..., Any]) -> None:
    """Un EmailData vacío produce un resultado vacío, sin error."""
    correo = fabrica_email_urls(texto="")

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    assert resultado.urls == []
    assert resultado.banderas == []
    assert resultado.estadisticas.total == 0


@pytest.mark.ac("AC-URL-07")
def test_entradas_malformadas_no_lanzan(fabrica_email_urls: Callable[..., Any]) -> None:
    """Esquemas rotos, espacios y una URL de 10 000 caracteres no revientan."""
    # 10 000 caracteres ya ejercita el camino de URL gigante (umbral: 200);
    # 100 000 hacía la prueba ~O(n^2) y tardan >35 s, explotación del gate.
    gigante = "http://" + "a" * 10_000
    texto = f"ht!tp://x/y http:// {gigante} https://exa mple.com/ //sin-esquema"
    correo = fabrica_email_urls(texto=texto)

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    assert isinstance(resultado.urls, list)
    assert any(u.original == gigante for u in resultado.urls)
    assert any("URL_LARGA" in u.codigos for u in resultado.urls)


@given(cadena=st.text(max_size=300))
@settings(max_examples=40, deadline=None)
def test_propiedad_arbitraria_no_lanza_excepcion(cadena: str) -> None:
    """Propiedad: ninguna cadena arbitraria provoca una excepción no controlada."""
    from src.level2_agent.models import EmailData

    correo = EmailData(htmlBody=cadena, textBody=cadena)
    resultado = analizar_urls(correo, deps=deps_de_prueba())
    assert resultado.estadisticas.total == len(resultado.urls)
