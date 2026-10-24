"""Configuración del análisis de adjuntos desde entorno (spec 005, research D10).

`ConfigAdjuntos` agrupa las listas de extensiones y los límites de zip. Se
construye con `defecto()` (constantes del M05) o `desde_entorno()` (variables
`ADJ_*`). Formato inválido → `ConfiguracionError` (fail-fast, Art. III.9).
"""

from __future__ import annotations

import os

from pydantic import BaseModel, field_validator
from src.level2_agent.adjuntos.modelos import (
    ADJ_LIMITE_DESCOMPRIMIDO_ZIP,
    ADJ_LIMITE_ENTRADAS_ZIP,
    ADJ_RATIO_MAXIMO_ZIP,
    EXTENSIONES_DOCUMENTAL_DEFAULT,
    EXTENSIONES_HTML_DEFAULT,
    EXTENSIONES_RIESGO_DEFAULT,
)


class ConfiguracionError(Exception):
    """Error de configuración del análisis de adjuntos (fail-fast, Art. III.9)."""


def _parsear_lista(valor: str) -> frozenset[str]:
    """Parsea una lista separada por coma: minúsculas, sin punto inicial, sin espacios."""
    partes: list[str] = []
    for token in valor.split(","):
        token = token.strip().lower().lstrip(".")
        if token:
            partes.append(token)
    return frozenset(partes)


class ConfigAdjuntos(BaseModel):
    """Configuración del análisis de adjuntos (listas + límites de zip)."""

    extensiones_riesgo: frozenset[str]
    extensiones_html: frozenset[str]
    extensiones_documental: frozenset[str]
    limite_entradas_zip: int
    limite_descomprimido_zip: int
    ratio_maximo_zip: int

    @field_validator("limite_entradas_zip", "limite_descomprimido_zip", "ratio_maximo_zip")
    @classmethod
    def _positivo(cls, v: int) -> int:
        """Valida que los límites sean positivos (Art. III.9)."""
        if v <= 0:
            raise ValueError("el límite debe ser positivo")  # noqa: TRY003
        return v

    @classmethod
    def defecto(cls) -> ConfigAdjuntos:
        """Configuración con los defaults del M05 (constantes nombradas)."""
        return cls(
            extensiones_riesgo=EXTENSIONES_RIESGO_DEFAULT,
            extensiones_html=EXTENSIONES_HTML_DEFAULT,
            extensiones_documental=EXTENSIONES_DOCUMENTAL_DEFAULT,
            limite_entradas_zip=ADJ_LIMITE_ENTRADAS_ZIP,
            limite_descomprimido_zip=ADJ_LIMITE_DESCOMPRIMIDO_ZIP,
            ratio_maximo_zip=ADJ_RATIO_MAXIMO_ZIP,
        )

    @classmethod
    def desde_entorno(cls) -> ConfigAdjuntos:
        """Lee las variables `ADJ_*` del entorno; usa defaults si están ausentes.

        Listas vacías en el entorno caen al default (conservador: más detección).
        Entero no numérico o ≤ 0 → `ConfiguracionError`.
        """
        try:
            return cls(
                extensiones_riesgo=_parsear_lista(
                    os.environ.get("ADJ_EXTENSIONES_RIESGO", "")
                ) or EXTENSIONES_RIESGO_DEFAULT,
                extensiones_html=_parsear_lista(
                    os.environ.get("ADJ_EXTENSIONES_HTML", "")
                ) or EXTENSIONES_HTML_DEFAULT,
                extensiones_documental=_parsear_lista(
                    os.environ.get("ADJ_EXTENSIONES_DOCUMENTO", "")
                ) or EXTENSIONES_DOCUMENTAL_DEFAULT,
                limite_entradas_zip=int(
                    os.environ.get("ADJ_LIMITE_ENTRADAS_ZIP", ADJ_LIMITE_ENTRADAS_ZIP)
                ),
                limite_descomprimido_zip=int(
                    os.environ.get("ADJ_LIMITE_DESCOMPRIMIDO_ZIP", ADJ_LIMITE_DESCOMPRIMIDO_ZIP)
                ),
                ratio_maximo_zip=int(
                    os.environ.get("ADJ_RATIO_MAXIMO_ZIP", ADJ_RATIO_MAXIMO_ZIP)
                ),
            )
        except (ValueError, TypeError) as exc:
            raise ConfiguracionError(
                f"configuración de adjuntos inválida: {exc}"
            ) from exc
