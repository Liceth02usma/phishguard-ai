"""AC-URL-04: la expansión no descarga el cuerpo de ninguna respuesta (FR-005).

(a) El adapter de producción usa `HEAD` con `stream=True` y cierra sin leer:
nunca toca `content`/`read`/`iter_content`. (b) Sobre el servidor local de
prueba, la expansión solo emite HEAD y el servidor no escribe cuerpos.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
import requests
from src.level2_agent.analisis_urls import analizar_urls
from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.puertos import ClienteHTTPRequests

from dobles_red import (
    ClienteHTTPServidorLocal,
    ResolvedorDNSDouble,
    deps_de_prueba,
    servidor_local,
)

_CONFIG = ConfigURLs(acortadores=frozenset({"corto.test"}))


class _RespuestaFalsa:
    """Respuesta fake de requests: registra cierres y revienta si leen el cuerpo."""

    def __init__(self, status: int, location: str | None = None) -> None:
        self.status_code = status
        self.headers: dict[str, str] = {} if location is None else {"Location": location}
        self.cerrada = False

    def close(self) -> None:
        """Marca la respuesta como cerrada sin leer cuerpo."""
        self.cerrada = True

    @property
    def content(self) -> bytes:
        """Prohibido: nadie descarga el cuerpo (AC-URL-04)."""
        raise AssertionError("el cuerpo de la respuesta fue leído")

    def read(self, *args: object, **kwargs: object) -> bytes:
        """Prohibido: nadie descarga el cuerpo (AC-URL-04)."""
        raise AssertionError("el cuerpo de la respuesta fue leído")

    def iter_content(self, *args: object, **kwargs: object) -> Any:
        """Prohibido: nadie descarga el cuerpo (AC-URL-04)."""
        raise AssertionError("el cuerpo de la respuesta fue leído")


def test_adapter_head_sin_cuerpo_y_cierre(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ClienteHTTPRequests` pide HEAD con stream y cierra sin tocar el cuerpo."""
    respuestas: list[_RespuestaFalsa] = []
    llamadas: list[dict[str, Any]] = []

    def _head(url: str, **kwargs: Any) -> _RespuestaFalsa:
        llamadas.append({"metodo": "HEAD", "url": url, **kwargs})
        respuesta = _RespuestaFalsa(301, "http://corto.test/p2")
        respuestas.append(respuesta)
        return respuesta

    monkeypatch.setattr(requests, "head", _head)

    cliente = ClienteHTTPRequests()
    respuesta = cliente.solicitar("http://corto.test/p1")

    assert llamadas[0]["allow_redirects"] is False
    assert llamadas[0]["stream"] is True
    assert respuesta.status == 301
    assert respuesta.location == "http://corto.test/p2"
    assert respuesta.ya_leido is False
    assert respuestas[0].cerrada is True


def test_adapter_falla_a_get_stream_sin_cuerpo(monkeypatch: pytest.MonkeyPatch) -> None:
    """405 en HEAD ⇒ fallback GET con stream y Range; también se cierra sin leer."""
    llamadas: list[dict[str, Any]] = []
    respuesta_get = _RespuestaFalsa(200)

    def _head(url: str, **kwargs: Any) -> _RespuestaFalsa:
        return _RespuestaFalsa(405)

    def _get(url: str, **kwargs: Any) -> _RespuestaFalsa:
        llamadas.append({"url": url, **kwargs})
        return respuesta_get

    monkeypatch.setattr(requests, "head", _head)
    monkeypatch.setattr(requests, "get", _get)

    cliente = ClienteHTTPRequests()
    respuesta = cliente.solicitar("http://corto.test/p1")

    assert llamadas[0]["allow_redirects"] is False
    assert llamadas[0]["stream"] is True
    assert llamadas[0]["headers"] == {"Range": "bytes=0-0"}
    assert respuesta.ya_leido is False
    assert respuesta_get.cerrada is True


@pytest.mark.ac("AC-URL-04")
def test_expansion_solo_emite_head_sobre_el_servidor(
    fabrica_email_urls: Callable[..., Any],
) -> None:
    """Con respuesta 200 final, el servidor solo ve HEAD y no escribe cuerpos."""
    correo = fabrica_email_urls(html='<a href="http://corto.test/fin">x</a>')
    dns = ResolvedorDNSDouble({"corto.test": ["93.184.216.34"]})

    with servidor_local({"/fin": (200, None)}) as servidor:
        http = ClienteHTTPServidorLocal(puerto=servidor.puerto)
        resultado = analizar_urls(
            correo, _CONFIG, deps_de_prueba(resolvedor=dns, http=http)
        )
        assert servidor.peticiones == ["HEAD /fin"]
        assert servidor.escrituras_cuerpo == 0

    url = next(u for u in resultado.urls if u.host == "corto.test")
    assert url.expansion is not None
    assert url.expansion.estado == "expandida"
    assert http.cuerpos_leidos == 0
