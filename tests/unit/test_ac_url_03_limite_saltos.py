"""AC-URL-03: la expansión se detiene a los 5 saltos o a los 5 s (FR-003).

Valores límite (research D10): cadenas de 4, 5 y 6 redirecciones y relojes
de 2.4 s/paso (sigue) y 2.5 s/paso (corta en el borde de 5 s). Al cortar
por límite se registra `REDIRECCION_EXCESIVA` (research D9).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from src.level2_agent.analisis_urls import analizar_urls
from src.level2_agent.analisis_urls.configuracion import ConfigURLs

from dobles_red import (
    ClienteHTTPDouble,
    RelojFalso,
    ResolvedorDNSDouble,
    deps_de_prueba,
)
from dobles_red import RespuestaRedireccion as Respuesta

_CONFIG = ConfigURLs(acortadores=frozenset({"corto.test"}))
_DNS = {"corto.test": ["93.184.216.34"]}
_FINAL = Respuesta(status=200, location=None)


def _cadena(n_redirecciones: int) -> list[Respuesta]:
    """Cadena de respuestas con `n` redirecciones hacia p2, p3, p4, ..."""
    return [
        Respuesta(status=302, location=f"http://corto.test/p{i + 2}")
        for i in range(n_redirecciones)
    ]


def _url_de(correo: Any) -> Any:
    return next(u for u in correo.urls if u.host == "corto.test")


@pytest.mark.ac("AC-URL-03")
def test_cuatro_saltos_expande_sin_bandera(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """4 saltos y respuesta final ⇒ expandida, sin REDIRECCION_EXCESIVA."""
    correo = fabrica_email_urls(html='<a href="http://corto.test/p1">x</a>')
    doble = ClienteHTTPDouble([*_cadena(3), _FINAL])

    resultado = analizar_urls(
        correo, _CONFIG, deps_de_prueba(resolvedor=ResolvedorDNSDouble(_DNS), http=doble)
    )

    url = _url_de(resultado)
    assert url.expansion is not None
    assert url.expansion.estado == "expandida"
    assert url.expansion.saltos == 4
    assert url.expansion.destino_final == "http://corto.test/p4"
    assert "REDIRECCION_EXCESIVA" not in url.codigos
    assert resultado.estadisticas.expandidas == 1


@pytest.mark.ac("AC-URL-03")
def test_cinco_saltos_corta_con_bandera(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """5.ª respuesta aún redirección ⇒ se detiene en el salto 5 con la bandera."""
    correo = fabrica_email_urls(html='<a href="http://corto.test/p1">x</a>')
    doble = ClienteHTTPDouble(_cadena(5))

    resultado = analizar_urls(
        correo, _CONFIG, deps_de_prueba(resolvedor=ResolvedorDNSDouble(_DNS), http=doble)
    )

    url = _url_de(resultado)
    assert url.expansion is not None
    assert url.expansion.estado == "limite_saltos"
    assert url.expansion.saltos == 5
    assert len(doble.peticiones) == 5
    assert "REDIRECCION_EXCESIVA" in url.codigos


@pytest.mark.ac("AC-URL-03")
def test_seis_saltos_nunca_hay_sexta_peticion(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Con cadena de 6, jamás se emite una 6.ª petición (tope 5) y hay bandera."""
    correo = fabrica_email_urls(html='<a href="http://corto.test/p1">x</a>')
    doble = ClienteHTTPDouble(_cadena(6))

    resultado = analizar_urls(
        correo, _CONFIG, deps_de_prueba(resolvedor=ResolvedorDNSDouble(_DNS), http=doble)
    )

    url = _url_de(resultado)
    assert url.expansion is not None
    assert url.expansion.estado == "limite_saltos"
    assert len(doble.peticiones) == 5
    assert "REDIRECCION_EXCESIVA" in url.codigos


@pytest.mark.ac("AC-URL-03")
def test_reloj_corta_en_el_borde_de_cinco_segundos(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """2.5 s por petición: tras dos saltos el reloj marca 5.0 s ⇒ limite_tiempo."""
    correo = fabrica_email_urls(html='<a href="http://corto.test/p1">x</a>')
    reloj = RelojFalso()

    def _paso(_url: str) -> Respuesta:
        reloj.avanzar(2.5)
        return Respuesta(status=302, location="http://corto.test/p2")

    doble = ClienteHTTPDouble([_paso, _paso, _paso])
    resultado = analizar_urls(
        correo,
        _CONFIG,
        deps_de_prueba(resolvedor=ResolvedorDNSDouble(_DNS), http=doble, reloj=reloj),
    )

    url = _url_de(resultado)
    assert url.expansion is not None
    assert url.expansion.estado == "limite_tiempo"
    assert url.expansion.saltos == 2
    assert "REDIRECCION_EXCESIVA" in url.codigos


@pytest.mark.ac("AC-URL-03")
def test_por_debajo_del_borde_sigue_expandiendo(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """2.4 s por petición: 4.8 s < 5 s ⇒ se hace un tercer salto antes de cortar."""
    correo = fabrica_email_urls(html='<a href="http://corto.test/p1">x</a>')
    reloj = RelojFalso()

    def _paso(_url: str) -> Respuesta:
        reloj.avanzar(2.4)
        return Respuesta(status=302, location="http://corto.test/p2")

    doble = ClienteHTTPDouble([_paso, _paso, _paso])
    resultado = analizar_urls(
        correo,
        _CONFIG,
        deps_de_prueba(resolvedor=ResolvedorDNSDouble(_DNS), http=doble, reloj=reloj),
    )

    url = _url_de(resultado)
    assert url.expansion is not None
    assert url.expansion.estado == "limite_tiempo"
    assert url.expansion.saltos == 3
    assert len(doble.peticiones) == 3
