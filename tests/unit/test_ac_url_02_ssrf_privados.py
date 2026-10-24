"""AC-URL-02: la expansión jamás se conecta a privadas/loopback/metadata (FR-004).

(a) DNS que resuelve a IP privada en el primer salto → cero peticiones al
servidor local de prueba. (b) Redirección del servidor local a 127.0.0.1 →
el segundo salto se bloquea y el servidor recibió exactamente UNA petición.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from src.level2_agent.analisis_urls import analizar_urls
from src.level2_agent.analisis_urls.configuracion import ConfigURLs

from dobles_red import (
    ClienteHTTPServidorLocal,
    ResolvedorDNSDouble,
    deps_de_prueba,
    servidor_local,
)

_CONFIG = ConfigURLs(acortadores=frozenset({"corto.test"}))


@pytest.mark.ac("AC-URL-02")
def test_dns_a_ip_privada_no_conecta(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Si el DNS del acortador resuelve a loopback, no se emite ninguna petición."""
    html = '<a href="http://corto.test/promo">x</a>'
    correo = fabrica_email_urls(html=html, texto="")
    dns = ResolvedorDNSDouble({"corto.test": ["127.0.0.1"]})

    with servidor_local({}) as servidor:
        http = ClienteHTTPServidorLocal(puerto=servidor.puerto)
        resultado = analizar_urls(
            correo, _CONFIG, deps_de_prueba(resolvedor=dns, http=http)
        )

    url = next(u for u in resultado.urls if u.host == "corto.test")
    assert url.expansion is not None
    assert url.expansion.estado == "bloqueada_ssrf"
    assert "127.0.0.1" in (url.expansion.motivo or "")
    assert servidor.peticiones == []
    assert resultado.estadisticas.bloqueadas_ssrf == 1


@pytest.mark.ac("AC-URL-02")
def test_redireccion_a_loopback_bloqueada_tras_una_peticion(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Una redirección a 127.0.0.1 se bloquea antes del segundo salto."""
    html = '<a href="http://corto.test/promo">x</a>'
    correo = fabrica_email_urls(html=html, texto="")
    dns = ResolvedorDNSDouble({"corto.test": ["93.184.216.34"]})

    rutas = {"/promo": (302, "http://127.0.0.1/robar")}
    with servidor_local(rutas) as servidor:
        http = ClienteHTTPServidorLocal(puerto=servidor.puerto)
        resultado = analizar_urls(
            correo, _CONFIG, deps_de_prueba(resolvedor=dns, http=http)
        )

    url = next(u for u in resultado.urls if u.host == "corto.test")
    assert url.expansion is not None
    assert url.expansion.estado == "bloqueada_ssrf"
    assert url.expansion.saltos == 1
    # Exactamente la petición del primer salto; jamás se pidió /robar.
    assert servidor.peticiones == ["HEAD /promo"]
    assert http.peticiones == ["http://corto.test/promo"]
    # El literal loopback no necesita DNS: solo se resolvió el acortador.
    assert dns.consultas == ["corto.test"]
