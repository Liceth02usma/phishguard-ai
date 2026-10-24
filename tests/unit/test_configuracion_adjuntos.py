"""Tests for ConfigAdjuntos.desde_entorno() and ConfiguracionError (T035).

Verifica que la lectura de variables de entorno funciona correctamente y que
entradas inválidas lanzan ConfiguracionError (fail-fast, Art. III.9).
"""

from __future__ import annotations

import pytest
from src.level2_agent.adjuntos.configuracion import (
    ConfigAdjuntos,
    ConfiguracionError,
    _parsear_lista,
)
from src.level2_agent.adjuntos.modelos import (
    ADJ_LIMITE_DESCOMPRIMIDO_ZIP,
    ADJ_LIMITE_ENTRADAS_ZIP,
    ADJ_RATIO_MAXIMO_ZIP,
    EXTENSIONES_DOCUMENTAL_DEFAULT,
    EXTENSIONES_HTML_DEFAULT,
    EXTENSIONES_RIESGO_DEFAULT,
)

_ADJ_VARS = [
    "ADJ_EXTENSIONES_RIESGO",
    "ADJ_EXTENSIONES_HTML",
    "ADJ_EXTENSIONES_DOCUMENTO",
    "ADJ_LIMITE_ENTRADAS_ZIP",
    "ADJ_LIMITE_DESCOMPRIMIDO_ZIP",
    "ADJ_RATIO_MAXIMO_ZIP",
]


def test_configuracion_error_is_exception() -> None:
    assert issubclass(ConfiguracionError, Exception)


def test_desde_entorno_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ADJ_VARS:
        monkeypatch.delenv(var, raising=False)
    config = ConfigAdjuntos.desde_entorno()
    assert config.extensiones_riesgo == EXTENSIONES_RIESGO_DEFAULT
    assert config.extensiones_html == EXTENSIONES_HTML_DEFAULT
    assert config.extensiones_documental == EXTENSIONES_DOCUMENTAL_DEFAULT
    assert config.limite_entradas_zip == ADJ_LIMITE_ENTRADAS_ZIP
    assert config.limite_descomprimido_zip == ADJ_LIMITE_DESCOMPRIMIDO_ZIP
    assert config.ratio_maximo_zip == ADJ_RATIO_MAXIMO_ZIP


def test_desde_entorno_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJ_EXTENSIONES_RIESGO", "exe,dll,js")
    monkeypatch.setenv("ADJ_LIMITE_ENTRADAS_ZIP", "50")
    monkeypatch.setenv("ADJ_RATIO_MAXIMO_ZIP", "200")
    config = ConfigAdjuntos.desde_entorno()
    assert config.extensiones_riesgo == frozenset({"exe", "dll", "js"})
    assert config.limite_entradas_zip == 50
    assert config.ratio_maximo_zip == 200


def test_desde_entorno_invalid_integer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJ_LIMITE_ENTRADAS_ZIP", "abc")
    with pytest.raises(ConfiguracionError):
        ConfigAdjuntos.desde_entorno()


def test_desde_entorno_zero_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJ_RATIO_MAXIMO_ZIP", "0")
    with pytest.raises(ConfiguracionError):
        ConfigAdjuntos.desde_entorno()


def test_desde_entorno_negative_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJ_LIMITE_DESCOMPRIMIDO_ZIP", "-1")
    with pytest.raises(ConfiguracionError):
        ConfigAdjuntos.desde_entorno()


def test_parsear_lista_normaliza() -> None:
    assert _parsear_lista("EXE,.DLL, js") == frozenset({"exe", "dll", "js"})
    assert _parsear_lista("") == frozenset()
    assert _parsear_lista(".PDF,.docx") == frozenset({"pdf", "docx"})
