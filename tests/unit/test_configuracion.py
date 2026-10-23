"""Pruebas de ConfigBanderas: env, defaults D9 y fail-fast (T006, Art. III.9)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from src.level2_agent.banderas.configuracion import (
    DEFAULT_DOMINIOS_GRATUITOS,
    ConfigBanderas,
    ConfiguracionError,
)

_VARIABLES_ENTORNO = (
    "AUTHSERV_ID",
    "DOMINIOS_PROPIOS",
    "MARCAS_PROTEGIDAS",
    "CONTACTOS_INTERNOS",
    "TERMINOS_INTERNOS",
    "DOMINIOS_GRATUITOS",
    "PROVEEDORES_ENVIO",
)


@pytest.fixture
def entorno_limpio(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Garantiza que las 7 variables M03 no vienen del entorno del desarrollador."""
    for variable in _VARIABLES_ENTORNO:
        monkeypatch.delenv(variable, raising=False)
    yield


def test_defaults_con_entorno_vacio(entorno_limpio: None) -> None:
    """authserv-id vacio (conservador) y los dominios gratuitos por defecto (D9)."""
    config = ConfigBanderas.desde_entorno()
    assert config.authserv_id == ""
    assert config.dominios_gratuitos == DEFAULT_DOMINIOS_GRATUITOS
    assert config.marcas_protegidas == frozenset()
    assert config.dominios_propios == frozenset()
    assert config.contactos_internos == frozenset()
    assert config.terminos_internos == frozenset()
    assert config.proveedores_envio == frozenset()


def test_listas_por_coma_en_minusculas(
    entorno_limpio: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Las listas env llegan separadas por coma y se normalizan a minusculas."""
    monkeypatch.setenv("AUTHSERV_ID", "  Mail.Empresa.COM ")
    monkeypatch.setenv("MARCAS_PROTEGIDAS", "PayPal.com, EJEMPLO.COM , , foo.net")
    monkeypatch.setenv("TERMINOS_INTERNOS", "Ayuda Interna, SOPORTE 24/7")
    config = ConfigBanderas.desde_entorno()
    assert config.authserv_id == "mail.empresa.com"
    assert config.marcas_protegidas == frozenset({"paypal.com", "ejemplo.com", "foo.net"})
    assert config.terminos_internos == frozenset({"ayuda interna", "soporte 24/7"})


def test_dominios_gratuitos_sustituibles_desde_entorno(
    entorno_limpio: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DOMINIOS_GRATUITOS de env reemplaza el default (D9)."""
    monkeypatch.setenv("DOMINIOS_GRATUITOS", "correo.uno.com,dos.cl")
    config = ConfigBanderas.desde_entorno()
    assert config.dominios_gratuitos == frozenset({"correo.uno.com", "dos.cl"})


@pytest.mark.parametrize(
    "valor_invalido",
    ["https://x.com", "x.com/ruta", "dominio con espacio", "sub.dominio..com", "-x.com"],
)
def test_dominios_invalidos_lanzan_configuracion_error(valor_invalido: str) -> None:
    """Un dominio con esquema, ruta, espacios o forma rara es fail-fast (Art. III.9)."""
    with pytest.raises(ConfiguracionError):
        ConfigBanderas(marcas_protegidas=[valor_invalido])


@pytest.mark.parametrize(
    "authserv_invalido",
    ["https://pasarela.com", "pasarela.com con espacio", "pasarela.com/ruta"],
)
def test_authserv_invalido_lanza_configuracion_error(authserv_invalido: str) -> None:
    """authserv-id con esquema, ruta o espacios es fail-fast (Art. III.9)."""
    with pytest.raises(ConfiguracionError):
        ConfigBanderas(authserv_id=authserv_invalido)


def test_authserv_none_y_punto_final(entorno_limpio: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """AUTHSERV_ID vacio/ausente -> ""; el punto final se recorta."""
    monkeypatch.setenv("AUTHSERV_ID", "Pasarela.Externa. ")
    config = ConfigBanderas.desde_entorno()
    assert config.authserv_id == "pasarela.externa"
    assert ConfigBanderas(authserv_id=None).authserv_id == ""
