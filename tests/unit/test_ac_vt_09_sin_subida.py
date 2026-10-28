"""AC-VT-09: con los flags por defecto ninguna petición POST; lo desconocido no se sube."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo, consultar_url
from src.level2_agent.virustotal.envios import enviar_url_desconocida, subir_archivo

from dobles_vt import (
    ClienteDoble,
    RespuestaDoble,
    cargar_respuesta,
    deps_prueba,
)

SHA = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
URL = "https://ejemplo.com/pagina-desconocida"
CONFIG = ConfigVT(api_key="clave-de-prueba")  # upload/submit por defecto False


def _sin_post(cliente: ClienteDoble) -> None:
    """Ningún caminito de la prueba emitió un POST (G10/FR-008)."""
    assert [p for p in cliente.peticiones if p.metodo == "POST"] == []


@pytest.mark.ac("AC-VT-09")
def test_archivo_desconocido_no_se_sube() -> None:
    """Hash con 404 → desconocida y cero POST hacia /files (FR-008)."""
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/files/{SHA}"): [
                RespuestaDoble(404, cargar_respuesta("no_encontrado.json"))
            ]
        }
    )
    resultado = consultar_archivo(SHA, config=CONFIG, deps=deps_prueba(cliente))
    assert resultado.clasificacion == "desconocida"
    assert resultado.fuente == "red"
    _sin_post(cliente)
    assert cliente.contar("POST", "/files") == 0


@pytest.mark.ac("AC-VT-09")
def test_url_desconocida_no_se_envia() -> None:
    """URL con 404 → desconocida y cero POST hacia /urls (FR-008)."""
    from src.level2_agent.virustotal.identificadores import id_url_base64

    identificador = id_url_base64(URL)
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/urls/{identificador}"): [
                RespuestaDoble(404, cargar_respuesta("no_encontrado.json"))
            ]
        }
    )
    resultado = consultar_url(URL, config=CONFIG, deps=deps_prueba(cliente))
    assert resultado.clasificacion == "desconocida"
    _sin_post(cliente)


@pytest.mark.ac("AC-VT-09")
def test_bandera_de_flags_desactivada_no_llama() -> None:
    """subir_archivo/enviar_url_desconocida cortan antes de armar la petición (FR-008)."""
    cliente = ClienteDoble()
    assert subir_archivo(SHA, b"contenido", config=CONFIG, deps=deps_prueba(cliente)) is False
    assert enviar_url_desconocida(URL, config=CONFIG, deps=deps_prueba(cliente)) is False
    assert cliente.peticiones == []


@pytest.mark.ac("AC-VT-09")
def test_flags_explícitamente_activos_sí_postean() -> None:
    """Con VT_UPLOAD_UNKNOWN=true el POST /files sí se emite (comportamiento documentado)."""
    config = ConfigVT(api_key="clave-de-prueba", upload_unknown=True)
    cliente = ClienteDoble(rutas={("POST", "/files"): [RespuestaDoble(200, {})]})
    assert subir_archivo(SHA, b"contenido", config=config, deps=deps_prueba(cliente)) is True
    assert cliente.contar("POST", "/files") == 1
