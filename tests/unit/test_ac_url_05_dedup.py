"""AC-URL-05: las URLs duplicadas tras normalizar se reportan una sola vez.

FR-001: deduplicar tras normalizar (host minúsculas, sin fragmento, sin
tracking) conservando la URL original y el orden de aparición.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from src.level2_agent.analisis_urls import analizar_urls

from dobles_red import deps_de_prueba


@pytest.mark.ac("AC-URL-05")
def test_duplicados_tras_normalizar_colapsan_a_una(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Mayúsculas, fragmento y tracking colapsan a UNA URL con la original intacta."""
    texto = (
        "HTTPS://Example.COM/a#frag "
        "https://example.com/a?utm_source=x "
        "https://example.com/a"
    )
    correo = fabrica_email_urls(texto=texto)

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    assert len(resultado.urls) == 1
    assert resultado.urls[0].original == "HTTPS://Example.COM/a#frag"
    assert resultado.urls[0].normalizada == "https://example.com/a"
    assert resultado.urls[0].host == "example.com"
    assert resultado.estadisticas.total == 1


@pytest.mark.ac("AC-URL-05")
def test_orden_de_aparicion_preservado(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """URLs distintas conservan el orden en que aparecen y no se duplican."""
    texto = "https://alpha.example/1 https://beta.example/2 https://alpha.example/1#otra"
    correo = fabrica_email_urls(texto=texto)

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    assert [u.host for u in resultado.urls] == ["alpha.example", "beta.example"]
    assert resultado.urls[0].original == "https://alpha.example/1"
