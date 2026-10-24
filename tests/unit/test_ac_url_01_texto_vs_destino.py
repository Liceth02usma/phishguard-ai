"""AC-URL-01: el texto de un enlace que muestra un dominio distinto al destino.

Activa `URL_TEXTO_DISTINTO_DESTINO` (20 pts, alta) y su negativa.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from src.level2_agent.analisis_urls import analizar_urls

from dobles_red import deps_de_prueba


@pytest.mark.ac("AC-URL-01")
def test_texto_distinto_del_destino_activa_la_bandera(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Un enlace con texto `https://banco.com` y destino `http://evil.example` activa la bandera."""
    html = '<a href="http://evil.example/login">https://banco.com</a>'
    correo = fabrica_email_urls(html=html, texto="")

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    destino = [u for u in resultado.urls if u.host == "evil.example"]
    assert destino, "la URL del href debe extraerse y analizarse"
    assert "URL_TEXTO_DISTINTO_DESTINO" in destino[0].codigos
    bandera = next(b for b in resultado.banderas if b.codigo == "URL_TEXTO_DISTINTO_DESTINO")
    assert bandera.puntos == 20
    assert bandera.severidad == "alta"
    assert "evil.example" in bandera.detalle


@pytest.mark.ac("AC-URL-01")
def test_texto_igual_al_destino_no_activa_la_bandera(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Un enlace cuyo texto muestra el mismo host que el destino no activa la bandera."""
    html = '<a href="https://banco.com/x">https://banco.com</a>'
    correo = fabrica_email_urls(html=html, texto="")

    resultado = analizar_urls(correo, deps=deps_de_prueba())

    assert resultado.urls
    assert all("URL_TEXTO_DISTINTO_DESTINO" not in u.codigos for u in resultado.urls)
