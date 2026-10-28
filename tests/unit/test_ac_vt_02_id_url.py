"""AC-VT-02: identificador Base64 url-safe sin relleno + idempotencia (propiedad)."""

from __future__ import annotations

import base64
import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.level2_agent.virustotal import ConfigVT, consultar_url
from src.level2_agent.virustotal.identificadores import id_url_base64

from dobles_vt import ClienteDoble, RespuestaDoble, cargar_respuesta, deps_prueba

URLS_CONOCIDAS = [
    "https://ejemplo.com/ruta/archivo?x=1&y=2",
    "https://ejemplo.com/con espacios/a b.html",
    "https://ejemplo.com/base64+padding=",
]
# `*` y no `+`: la entrada vacía produce id vacío, que también es url-safe.
PATRON_URL_SAFE = re.compile(r"^[A-Za-z0-9_-]*$")


@pytest.mark.ac("AC-VT-02")
@pytest.mark.parametrize("url", URLS_CONOCIDAS)
def test_id_url_base64_url_safe_sin_relleno(url: str) -> None:
    """El id es url-safe B64 sin '=' y equivale al encode canónico de la URL."""
    identificador = id_url_base64(url)
    assert PATRON_URL_SAFE.fullmatch(identificador) is not None
    esperado = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
    assert identificador == esperado


@pytest.mark.ac("AC-VT-02")
def test_transporte_recibe_get_urls_id() -> None:
    """El camino completo usa GET /urls/{id} con el id calculado (M06.2)."""
    url = "https://ejemplo.com/ruta/archivo?x=1&y=2"
    identificador = id_url_base64(url)
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/urls/{identificador}"): [
                RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))
            ]
        }
    )
    resultado = consultar_url(
        url, config=ConfigVT(api_key="clave-de-prueba"), deps=deps_prueba(cliente)
    )
    assert cliente.contar("GET", f"/urls/{identificador}") == 1
    assert resultado.clasificacion == "maliciosa"


@given(st.text(max_size=200))
@settings(deadline=None, max_examples=50)
@pytest.mark.ac("AC-VT-02")
def test_propiedad_id_url_safe_e_idempotente(url: str) -> None:
    """PAR-001: cualquier entrada produce id url-safe y la llamada repetida es estable."""
    identificador = id_url_base64(url)
    assert PATRON_URL_SAFE.fullmatch(identificador) is not None
    assert id_url_base64(url) == identificador
