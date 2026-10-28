"""AC-VT-07: saneado de 7 parámetros + valores con forma de correo; jamás loguea la clave."""

from __future__ import annotations

import base64
import logging
from urllib.parse import parse_qsl, urlsplit

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo, consultar_url
from src.level2_agent.virustotal.identificadores import id_url_base64
from tests.unit.dobles_vt import (
    ClienteDoble,
    RespuestaDoble,
    cargar_respuesta,
    deps_prueba,
)

CONFIG = ConfigVT(api_key="supersecreta-clave-vt-98765")
SHA = "00" * 32


def _url_con_sensibles() -> str:
    """URL con los 7 parámetros sensibles literales de FR-007 y dos correos sueltos."""
    return (
        "https://ejemplo.com/descarga?token=abc123&key=xyz&session=s1"
        "&email=ana@ejemplo.com&user=ana&code=9988&password=hunter2"
        "&otra=valor&contacto=juan.perez@empresa.com"
    )


def _url_recibida(cliente: ClienteDoble) -> str:
    """Decodifica el id Base64 de la única petición GET /urls/... a la URL original."""
    peticiones = [p for p in cliente.peticiones if p.metodo == "GET"]
    assert peticiones, "no hubo petición GET /urls"
    identificador = peticiones[0].path.removeprefix("/urls/")
    relleno = "=" * (-len(identificador) % 4)
    return base64.urlsafe_b64decode(identificador + relleno).decode("utf-8")


@pytest.mark.ac("AC-VT-07")
def test_transporte_recibe_url_saneada() -> None:
    """Nunca se envía la URL con parámetros sensibles ni valores con forma de correo."""
    url = _url_con_sensibles()
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/urls/{id_url_base64(url)}"): [
                RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))
            ]
        }
    )
    consultar_url(url, config=CONFIG, deps=deps_prueba(cliente))
    recibida = _url_recibida(cliente)
    parametros = dict(parse_qsl(urlsplit(recibida).query))
    for sensible in ("token", "key", "session", "email", "user", "code", "password"):
        assert sensible not in parametros, f"el parámetro {sensible} viajó sin sanear"
    assert parametros == {"otra": "valor"}
    assert "ana@ejemplo.com" not in recibida
    assert "juan.perez@empresa.com" not in recibida
    assert "hunter2" not in recibida


@pytest.mark.ac("AC-VT-07")
def test_clave_ausente_en_logs(caplog: pytest.LogCaptureFixture) -> None:
    """La clave nunca aparece en logs, mensajes ni errores (FR-009, AC-VT-07)."""
    cliente = ClienteDoble(
        rutas={("GET", f"/files/{SHA}"): [RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))]}
    )
    with caplog.at_level(logging.DEBUG):
        consultar_archivo(SHA, config=CONFIG, deps=deps_prueba(cliente))
    for registro in caplog.records:
        assert "supersecreta-clave-vt-98765" not in registro.getMessage()
