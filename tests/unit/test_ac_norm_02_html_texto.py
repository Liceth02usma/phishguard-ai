"""AC-NORM-02: HTML con script, texto oculto y comentario produce texto limpio."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from src.level2_agent.normalizacion import normalizar_desde_eml
from src.level2_agent.normalizacion.html_a_texto import _ExtractorTexto, html_a_texto


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


@pytest.mark.ac("AC-NORM-02")
def test_color_igual_al_fondo_oculta_texto(fabrica_eml: Callable[..., bytes]) -> None:
    """Elimina texto con color igual al fondo; conserva el de distinto color (FR-003)."""
    html = (
        '<div style="color:#ffffff;background-color:#ffffff">SECRETO</div>'
        '<div style="color:#000000;background-color:#ffffff">VISIBLE</div>'
    )
    eml = fabrica_eml(html=html, texto=None)
    resultado = normalizar_desde_eml(eml)
    assert "VISIBLE" in resultado.texto_limpio
    assert "SECRETO" not in resultado.texto_limpio


@pytest.mark.ac("AC-NORM-02")
def test_etiqueta_anidada_en_script_se_descarta(fabrica_eml: Callable[..., bytes]) -> None:
    """Una etiqueta anidada dentro de `<script>` se descarta sin contaminar el texto (FR-003)."""
    html = '<script>var x = "<b>no-negrita</b>";</script>final'
    eml = fabrica_eml(html=html, texto=None)
    resultado = normalizar_desde_eml(eml)
    assert "final" in resultado.texto_limpio
    assert "no-negrita" not in resultado.texto_limpio


@pytest.mark.ac("AC-NORM-06")
def test_html_malformado_devuelve_parcial(fabrica_eml: Callable[..., bytes]) -> None:
    """HTML malformado sin cerrar no lanza y devuelve el texto parcial (AC-NORM-06)."""
    eml = fabrica_eml(html="<div><span>unclosed", texto=None)
    resultado = normalizar_desde_eml(eml)
    assert "unclosed" in resultado.texto_limpio


def test_fallback_si_feed_lanza(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si `feed` lanza, `html_a_texto` devuelve lo parcial en vez de propagar (AC-NORM-06)."""
    real_feed = _ExtractorTexto.feed

    def feed_que_lanza(self: _ExtractorTexto, data: str) -> None:
        real_feed(self, "<p>parcial")
        raise RuntimeError("boom")

    monkeypatch.setattr(_ExtractorTexto, "feed", feed_que_lanza)
    assert html_a_texto("<p>parcial") == "parcial"
