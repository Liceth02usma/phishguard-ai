"""AC-NORM-03: cada límite de FR-004 activa `LIMITE_EXCEDIDO` (límite exacto y +1)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from src.level2_agent.models import Adjunto
from src.level2_agent.normalizacion import (
    BANDERA_LIMITE_EXCEDIDO,
    LIMITE_ADJUNTOS,
    LIMITE_BYTES_CORREO,
    LIMITE_CARACTERES_TEXTO,
    LIMITE_NIVELES_MIME,
    LIMITE_URLS,
    normalizar_desde_eml,
)
from src.level2_agent.normalizacion.limites import evaluar_limites


def _adjunto() -> Adjunto:
    """Adjunto de prueba válido (sha256 de longitud 64)."""
    return Adjunto(nombre="a.txt", tipo_declarado="text/plain", sha256="a" * 64)


# --- Valores límite vía la función pura (una prueba por límite) ---


@pytest.mark.ac("AC-NORM-03")
def test_bytes_en_limite_y_excedido() -> None:
    dentro = evaluar_limites(LIMITE_BYTES_CORREO, "", [], [], 1)
    assert dentro.bandera is None
    fuera = evaluar_limites(LIMITE_BYTES_CORREO + 1, "", [], [], 1)
    assert fuera.bandera == BANDERA_LIMITE_EXCEDIDO


@pytest.mark.ac("AC-NORM-03")
def test_texto_en_limite_y_excedido() -> None:
    dentro = evaluar_limites(10, "x" * LIMITE_CARACTERES_TEXTO, [], [], 1)
    assert dentro.bandera is None
    assert len(dentro.texto_limpio) == LIMITE_CARACTERES_TEXTO
    fuera = evaluar_limites(10, "x" * (LIMITE_CARACTERES_TEXTO + 1), [], [], 1)
    assert fuera.bandera == BANDERA_LIMITE_EXCEDIDO
    assert len(fuera.texto_limpio) == LIMITE_CARACTERES_TEXTO  # acotado


@pytest.mark.ac("AC-NORM-03")
def test_urls_en_limite_y_excedido() -> None:
    dentro = evaluar_limites(10, "", [f"https://e{i}.com" for i in range(LIMITE_URLS)], [], 1)
    assert dentro.bandera is None
    fuera = evaluar_limites(
        10, "", [f"https://e{i}.com" for i in range(LIMITE_URLS + 1)], [], 1
    )
    assert fuera.bandera == BANDERA_LIMITE_EXCEDIDO
    assert len(fuera.urls) == LIMITE_URLS  # conserva las primeras 200


@pytest.mark.ac("AC-NORM-03")
def test_adjuntos_en_limite_y_excedido() -> None:
    dentro = evaluar_limites(10, "", "", [_adjunto() for _ in range(LIMITE_ADJUNTOS)], 1)
    assert dentro.bandera is None
    fuera = evaluar_limites(10, "", "", [_adjunto() for _ in range(LIMITE_ADJUNTOS + 1)], 1)
    assert fuera.bandera == BANDERA_LIMITE_EXCEDIDO
    assert len(fuera.adjuntos) == LIMITE_ADJUNTOS  # conserva los primeros 20


@pytest.mark.ac("AC-NORM-03")
def test_profundidad_mime_en_limite_y_excedido() -> None:
    dentro = evaluar_limites(10, "", "", [], LIMITE_NIVELES_MIME)
    assert dentro.bandera is None
    fuera = evaluar_limites(10, "", "", [], LIMITE_NIVELES_MIME + 1)
    assert fuera.bandera == BANDERA_LIMITE_EXCEDIDO


# --- Extremo a extremo: el pipeline acota de verdad ---


@pytest.mark.ac("AC-NORM-03")
def test_pipeline_acota_urls(fabrica_eml: Callable[..., bytes]) -> None:
    html = "<html><body>" + "".join(
        f"<a href='https://s{i}.com'>l{i}</a>" for i in range(LIMITE_URLS + 1)
    ) + "</body></html>"
    eml = fabrica_eml(html=html, texto=None)
    resultado = normalizar_desde_eml(eml)
    assert BANDERA_LIMITE_EXCEDIDO in resultado.banderas
    assert resultado.revision_manual is True
    assert len(resultado.urls) == LIMITE_URLS


@pytest.mark.ac("AC-NORM-03")
def test_pipeline_acota_adjuntos(fabrica_eml: Callable[..., bytes]) -> None:
    adjuntos = [(f"a{i}.txt", "text/plain", b"x") for i in range(LIMITE_ADJUNTOS + 1)]
    eml = fabrica_eml(adjuntos=adjuntos)
    resultado = normalizar_desde_eml(eml)
    assert BANDERA_LIMITE_EXCEDIDO in resultado.banderas
    assert len(resultado.adjuntos) == LIMITE_ADJUNTOS


@pytest.mark.ac("AC-NORM-03")
def test_pipeline_trunca_texto(fabrica_eml: Callable[..., bytes]) -> None:
    eml = fabrica_eml(texto="y" * (LIMITE_CARACTERES_TEXTO + 100))
    resultado = normalizar_desde_eml(eml)
    assert BANDERA_LIMITE_EXCEDIDO in resultado.banderas
    assert len(resultado.texto_limpio) <= LIMITE_CARACTERES_TEXTO


@pytest.mark.ac("AC-NORM-03")
def test_sin_bandera_en_flujo_normal(fabrica_eml: Callable[..., bytes]) -> None:
    """Un correo dentro de todos los límites no lleva `LIMITE_EXCEDIDO`."""
    eml = fabrica_eml(texto="cuerpo corto")
    resultado = normalizar_desde_eml(eml)
    assert BANDERA_LIMITE_EXCEDIDO not in resultado.banderas
    assert resultado.revision_manual is False
