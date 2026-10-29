"""Tabla de los 13 códigos del catálogo 5.2: par positivo/negativo por código (I5).

Severidad y puntos deben ser idénticos a la transcripción del catálogo
(`CATALOGO_URL`), y ningún código `VT_*` puede emitirse jamás (VI.1: los
`VT_*` son de la spec 006).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from src.level2_agent.analisis_urls import analizar_urls
from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.modelos import CATALOGO_URL

from dobles_red import ClienteHTTPDouble, RelojFalso, ResolvedorDNSDouble, deps_de_prueba
from dobles_red import RespuestaRedireccion as Respuesta

_PRESENCIA = [
    ("URL_TEXTO_DISTINTO_DESTINO", '<a href="http://evil.example/">https://banco.com</a>'),
    ("URL_HOST_IP", '<a href="http://8.8.8.8/x">x</a>'),
    ("URL_ACORTADA", '<a href="https://bit.ly/abc">x</a>'),
    ("URL_ARROBA", '<a href="http://banco.com@evil.example/">x</a>'),
    ("URL_PUNYCODE", '<a href="http://xn--e1awd7f.example/">x</a>'),
    ("URL_TLD_RIESGO", '<a href="http://malware.zip/x">x</a>'),
    ("URL_SUBDOMINIOS_EXCESIVOS", '<a href="http://a1.a2.a3.a4.a5.example.com/x">x</a>'),
    ("URL_PUERTO_NO_ESTANDAR", '<a href="http://example.com:8080/x">x</a>'),
    ("URL_HTTP_SIN_CIFRADO", '<a href="http://example.com/x">x</a>'),
    ("URL_LARGA", f'<a href="http://example.com/{"a" * 182}">x</a>'),
    ("URL_PARAMETROS_SENSIBLES", '<a href="http://example.com/?token=abc">x</a>'),
]

AUSENCIA = [
    ("URL_TEXTO_DISTINTO_DESTINO", '<a href="https://banco.com/x">https://banco.com</a>'),
    ("URL_HOST_IP", '<a href="http://example.com/x">x</a>'),
    ("URL_ACORTADA", '<a href="http://example.com/x">x</a>'),
    ("URL_ARROBA", '<a href="http://evil.example/x">x</a>'),
    ("URL_PUNYCODE", '<a href="http://plain.example/x">x</a>'),
    ("URL_TLD_RIESGO", '<a href="http://example.com/x">x</a>'),
    ("URL_SUBDOMINIOS_EXCESIVOS", '<a href="http://a.example.com/x">x</a>'),
    ("URL_PUERTO_NO_ESTANDAR", '<a href="https://example.com:443/x">x</a>'),
    ("URL_HTTP_SIN_CIFRADO", '<a href="https://example.com/x">x</a>'),
    ("URL_LARGA", f'<a href="http://example.com/{"a" * 181}">x</a>'),
    ("URL_PARAMETROS_SENSIBLES", '<a href="http://example.com/?page=2">x</a>'),
]


def test_catalogo_tiene_13_codigos_sin_vt() -> None:
    """El catálogo es exactamente el 5.2: 13 códigos de URL, cero `VT_*`."""
    assert len(CATALOGO_URL) == 13
    assert all(codigo.startswith(("URL_", "REDIRECCION_")) for codigo in CATALOGO_URL)
    assert not any(codigo.startswith("VT_") for codigo in CATALOGO_URL)


@pytest.mark.parametrize(("codigo", "html"), _PRESENCIA, ids=[c for c, _ in _PRESENCIA])
def test_positivo_por_codigo(
    codigo: str, html: str, fabrica_email_urls: Callable[..., Any]
) -> None:
    """Cada código del catálogo tiene un caso que lo activa, con puntos/severidad del catálogo."""
    correo = fabrica_email_urls(html=html, texto="")

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    assert codigo in resultado.urls[0].codigos
    bandera = next(b for b in resultado.banderas if b.codigo == codigo)
    # `codigo` llega como literal del catálogo (parametrize); el índice evita el cast.
    severidad, puntos = CATALOGO_URL[codigo]  # type: ignore[index]
    assert bandera.severidad == severidad
    assert bandera.puntos == puntos


@pytest.mark.parametrize(("codigo", "html"), AUSENCIA, ids=[c for c, _ in AUSENCIA])
def test_negativo_por_codigo(
    codigo: str, html: str, fabrica_email_urls: Callable[..., Any]
) -> None:
    """Cada código tiene un caso controlado que NO lo activa (falso positivo)."""
    correo = fabrica_email_urls(html=html, texto="")

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    assert codigo not in resultado.urls[0].codigos


def test_redireccion_excesiva_solo_por_limite(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """`REDIRECCION_EXCESIVA` solo aparece al cortar por límite, no al expandir limpio."""
    config = ConfigURLs(acortadores=frozenset({"corto.test"}))
    dns = ResolvedorDNSDouble({"corto.test": ["93.184.216.34"]})

    cadena = [
        Respuesta(status=302, location="http://corto.test/p2") for _ in range(5)
    ]
    correo_corta = fabrica_email_urls(html='<a href="http://corto.test/p1">x</a>')
    r_corta = analizar_urls(
        correo_corta, config, deps_de_prueba(resolvedor=dns, http=ClienteHTTPDouble(cadena))
    )
    assert "REDIRECCION_EXCESIVA" in r_corta.urls[0].codigos

    correo_limpia = fabrica_email_urls(html='<a href="http://corto.test/p1">x</a>')
    doble_limpia = ClienteHTTPDouble([Respuesta(status=200, location=None)])
    r_limpia = analizar_urls(
        correo_limpia, config, deps_de_prueba(resolvedor=dns, http=doble_limpia)
    )
    assert "REDIRECCION_EXCESIVA" not in r_limpia.urls[0].codigos


class _RDAP:
    """Doble de RDAP con edad fija (29/30/None según se necesite)."""

    def __init__(self, dias: int | None) -> None:
        self._dias = dias

    def antiguedad_dias(self, dominio: str) -> int | None:
        """Devuelve la edad fija configurada."""
        return self._dias


@pytest.mark.parametrize(
    ("dias", "esperado"), [(29, True), (30, False), (31, False), (None, False)]
)
def test_dominio_nuevo_borde_30_dias(
    dias: int | None, esperado: bool, fabrica_email_urls: Callable[..., Any]
) -> None:
    """`URL_DOMINIO_NUEVO` se activa SOLO con edad estrictamente menor a 30 días."""
    correo = fabrica_email_urls(html='<a href="http://nuevo.example/x">x</a>')
    reloj = RelojFalso()

    resultado = analizar_urls(
        correo,
        deps=deps_de_prueba(rdap=_RDAP(dias), reloj=reloj),
    )

    activada = "URL_DOMINIO_NUEVO" in resultado.urls[0].codigos
    assert activada is esperado
