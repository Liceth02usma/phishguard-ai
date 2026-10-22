"""AC-NORM-02: HTML con script, texto oculto y comentario produce texto limpio."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from src.level2_agent.normalizacion import normalizar_desde_eml


@pytest.mark.ac("AC-NORM-02")
def test_html_limpio_sin_scripts_estilos_comentarios(
    fabrica_eml: Callable[..., bytes], fabrica_html_oculto: Callable[[str], str]
) -> None:
    """El texto limpio conserva el texto visible y elimina script, ocultos y comentarios."""
    html = fabrica_html_oculto("VISIBLE")
    eml = fabrica_eml(html=html, texto=None)
    resultado = normalizar_desde_eml(eml)

    limpio = resultado.texto_limpio
    assert "VISIBLE" in limpio  # texto del enlace conservado (FR-003)
    assert "alert" not in limpio  # <script> eliminado
    assert "comentario oculto" not in limpio  # comentario eliminado
    assert "VISIBLE-oculto" not in limpio  # display:none eliminado
    assert "VISIBLE-cero" not in limpio  # font-size:0 eliminado


@pytest.mark.ac("AC-NORM-02")
def test_estilo_no_vaza_al_texto(
    fabrica_eml: Callable[..., bytes]
) -> None:
    """El CSS de `<style>` no aparece en el texto limpio."""
    html = (
        "<html><head><style>p{color:red;font-size:9px}</style></head>"
        "<body><p>hola</p></body></html>"
    )
    eml = fabrica_eml(html=html, texto=None)
    resultado = normalizar_desde_eml(eml)

    assert "hola" in resultado.texto_limpio
    assert "color" not in resultado.texto_limpio
    assert "font-size" not in resultado.texto_limpio


@pytest.mark.ac("AC-NORM-02")
def test_texto_plano_conservado(fabrica_eml: Callable[..., bytes]) -> None:
    """La parte `text/plain` se conserva en `texto_limpio`."""
    eml = fabrica_eml(texto="linea de texto plano")
    resultado = normalizar_desde_eml(eml)
    assert "linea de texto plano" in resultado.texto_limpio
