"""AC-URL-06: los parámetros sensibles se sanean antes de salir a consulta externa.

FR-007: los 7 nombres literales de la spec (`token`, `key`, `session`,
`email`, `user`, `code`, `password`) y los valores con forma de correo no
cruzan el límite del puerto HTTP (invariante I3, research D10.4/D12).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.level2_agent.analisis_urls import analizar_urls

from dobles_red import ClienteHTTPDouble, ResolvedorDNSDouble, deps_de_prueba
from dobles_red import RespuestaRedireccion as Respuesta


@pytest.mark.ac("AC-URL-06")
def test_token_y_email_no_llegan_al_puerto_http(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """`?token=abc&email=a@b.com` se sanea antes de la petición real."""
    html = (
        '<a href="https://bit.ly/3xAb?utm_source=mail&token=abc123'
        '&email=j.perez@banco.com">x</a>'
    )
    correo = fabrica_email_urls(html=html, texto="")
    doble = ClienteHTTPDouble([Respuesta(status=200, location=None)])
    dns = ResolvedorDNSDouble({"bit.ly": ["93.184.216.34"]})

    resultado = analizar_urls(
        correo, deps=deps_de_prueba(resolvedor=dns, http=doble)
    )

    assert doble.peticiones == ["https://bit.ly/3xAb"]
    url = resultado.urls[0]
    assert url.expansion is not None
    assert url.expansion.estado == "expandida"
    # El reporte interno conserva la original completa (FR-001).
    assert "token=abc123" in url.original


@given(valor=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=40))
@settings(max_examples=25, deadline=None)
def test_propiedad_ningun_valor_sensible_sobrevive(valor: str) -> None:
    """Propiedad: el valor de un parámetro sensible nunca aparece en la URL enviada."""
    html = f'<a href="https://bit.ly/x?token={valor}">a</a>'
    from src.level2_agent.models import EmailData

    correo = EmailData(htmlBody=html)
    doble = ClienteHTTPDouble([Respuesta(status=200, location=None)])
    dns = ResolvedorDNSDouble({"bit.ly": ["93.184.216.34"]})

    analizar_urls(correo, deps=deps_de_prueba(resolvedor=dns, http=doble))

    assert doble.peticiones
    enviado = doble.peticiones[0]
    assert "token=" not in enviado
    assert valor not in enviado


@pytest.mark.ac("AC-URL-06")
def test_valor_con_forma_de_cualquier_parametro_se_elimina(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Un valor con forma de correo se elimina aunque el nombre no sea sensible."""
    html = '<a href="https://bit.ly/x?contacto=j.perez@banco.com">a</a>'
    correo = fabrica_email_urls(html=html, texto="")
    doble = ClienteHTTPDouble([Respuesta(status=200, location=None)])
    dns = ResolvedorDNSDouble({"bit.ly": ["93.184.216.34"]})

    analizar_urls(correo, deps=deps_de_prueba(resolvedor=dns, http=doble))

    assert doble.peticiones == ["https://bit.ly/x"]
    assert "@" not in doble.peticiones[0]


@pytest.mark.ac("AC-URL-06")
def test_parametros_inofensivos_se_conservan(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Parámetros no sensibles sobreviven al saneado (no se destruye información)."""
    html = '<a href="https://bit.ly/x?subject=hola&page=2">a</a>'
    correo = fabrica_email_urls(html=html, texto="")
    doble = ClienteHTTPDouble([Respuesta(status=200, location=None)])
    dns = ResolvedorDNSDouble({"bit.ly": ["93.184.216.34"]})

    analizar_urls(correo, deps=deps_de_prueba(resolvedor=dns, http=doble))

    assert doble.peticiones == ["https://bit.ly/x?subject=hola&page=2"]


def test_sin_correos_en_detalles_de_banderas(
    fabrica_email_urls: Callable[..., Any],
) -> None:  # Art. V.4 — guardia adicional sobre los detalles
    """Ningún detalle de bandera contiene una dirección de correo completa."""
    html = '<a href="https://bit.ly/x?email=j.perez@banco.com">a</a>'
    correo = fabrica_email_urls(html=html, texto="")
    doble = ClienteHTTPDouble([Respuesta(status=200, location=None)])
    dns = ResolvedorDNSDouble({"bit.ly": ["93.184.216.34"]})

    resultado = analizar_urls(correo, deps=deps_de_prueba(resolvedor=dns, http=doble))

    assert resultado.banderas
    assert all("@" not in b.detalle for b in resultado.banderas)
