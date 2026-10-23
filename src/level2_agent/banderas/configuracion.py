"""Configuracion de las banderas de cabeceras (spec 003, research D9).

Listas configurables via variables de entorno (Art. III.6). Con ``AUTHSERV_ID``
vacio ninguna cabecera es de confianza: resultado conservador ``AUTH_NO_EVALUABLE``
(fallar hacia revisar, Art. V.1). Un formato invalido lanza ``ConfiguracionError``
al construir (fail-fast, Art. III.9).
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ValidationError, ValidationInfo, field_validator

# Forma de un dominio aceptada: etiquetas alfanumericas/guion, punto como separador.
_RE_DOMINIO = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")

DEFAULT_DOMINIOS_GRATUITOS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "hotmail.com",
        "outlook.com",
        "yahoo.com",
        "live.com",
        "icloud.com",
        "proton.me",
        "protonmail.com",
    }
)
"""Dominios gratuitos por defecto (decision de diseno D9, sustituibles via env)."""


class ConfiguracionError(ValueError):
    """Formato de configuracion invalido; se lanza al construir (Art. III.9)."""


def _como_lista(valor: Iterable[str] | None) -> list[str]:
    """Convierte el valor crudo en lista de strings (None -> vacia)."""
    if valor is None:
        return []
    return [str(x) for x in valor]


def _normalizar_dominios(campo: str, valores: Iterable[str] | None) -> frozenset[str]:
    """Normaliza y valida una lista de dominios; lanza ``ValueError`` si alguno es invalido."""
    limpios: set[str] = set()
    for bruto in _como_lista(valores):
        d = bruto.strip().lower().rstrip(".")
        if not d:
            continue
        if "/" in d or "://" in d or " " in d or not _RE_DOMINIO.match(d):
            raise ValueError(f"{campo}: dominio invalido '{bruto}'")
        limpios.add(d)
    return frozenset(limpios)


def _normalizar_textos(valores: Iterable[str] | None) -> frozenset[str]:
    """Normaliza una lista de textos libres (nombres/frases): minusculas, sin vacios."""
    return frozenset(t.strip().lower() for t in _como_lista(valores) if t.strip())


class ConfigBanderas(BaseModel):
    """Authserv-id propio y listas configurables de banderas (research D9)."""

    authserv_id: str = ""
    dominios_propios: frozenset[str] = frozenset()
    marcas_protegidas: frozenset[str] = frozenset()
    contactos_internos: frozenset[str] = frozenset()
    terminos_internos: frozenset[str] = frozenset()
    dominios_gratuitos: frozenset[str] = DEFAULT_DOMINIOS_GRATUITOS
    proveedores_envio: frozenset[str] = frozenset()

    def __init__(self, **data: Any) -> None:
        try:
            super().__init__(**data)
        except ValidationError as exc:
            raise ConfiguracionError(str(exc)) from exc

    @field_validator(
        "dominios_propios",
        "marcas_protegidas",
        "dominios_gratuitos",
        "proveedores_envio",
        mode="before",
    )
    @classmethod
    def _validar_dominios(cls, v: Iterable[str] | None, info: ValidationInfo) -> frozenset[str]:
        return _normalizar_dominios(str(info.field_name), v)

    @field_validator("contactos_internos", "terminos_internos", mode="before")
    @classmethod
    def _validar_textos(cls, v: Iterable[str] | None) -> frozenset[str]:
        return _normalizar_textos(v)

    @field_validator("authserv_id", mode="before")
    @classmethod
    def _validar_authserv(cls, v: Any) -> str:
        if v is None:
            return ""
        s = str(v).strip().lower()
        if s and ("/" in s or "://" in s or " " in s):
            raise ValueError(f"authserv_id invalido: {v!r}")
        return s.rstrip(".")

    @classmethod
    def desde_entorno(cls) -> ConfigBanderas:
        """Construye la config leyendo las variables de entorno (listas por coma)."""
        campos_dominios = (
            "dominios_propios",
            "marcas_protegidas",
            "dominios_gratuitos",
            "proveedores_envio",
        )
        campos_textos = ("contactos_internos", "terminos_internos")
        datos: dict[str, Any] = {"authserv_id": os.environ.get("AUTHSERV_ID", "")}
        for campo in (*campos_dominios, *campos_textos):
            crudo = os.environ.get(campo.upper(), "")
            if crudo.strip():
                datos[campo] = [x for x in crudo.split(",") if x.strip()]
        return cls(**datos)
