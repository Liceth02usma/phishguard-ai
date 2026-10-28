"""Configuración del cliente VirusTotal (spec 006, research D9).

Lee las variables LITERALES de la tabla 14.x del plan maestro:
`VT_TIER`, `VT_RPM`, `VT_DAILY`, `VT_MAX_POR_CORREO`, `VT_UPLOAD_UNKNOWN`,
`VT_SUBMIT_UNKNOWN_URLS` y los umbrales `VT_UMBRAL_*` (nombres decisión
propia documentada en D9; valores 3/3/20 literales de M06.4).

El modo `public` es solo para demostración: su uso en productos o servicios
comerciales no está permitido por los términos de VirusTotal (FR-002, Art. V.7).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Final, Literal

from pydantic import BaseModel, Field, ValidationError
from src.level2_agent.virustotal.modelos import (
    MAX_CONSULTAS_POR_CORREO,
    TOPE_DIA_PUBLIC,
    TOPE_RPM_PUBLIC,
    UMBRAL_LIMPIA,
    UMBRAL_MALICIOSA,
    UMBRAL_SOSPECHOSA,
)

TierVT = Literal["public", "premium"]


class ConfiguracionError(ValueError):
    """Configuración inválida detectada antes de consultar (Art. III.9)."""


_TRUE: Final[frozenset[str]] = frozenset({"true", "1", "yes"})


class ConfigVT(BaseModel):
    """Configuración inyectable del cliente VirusTotal (research D9).

    `api_key` solo se lee del entorno (`VT_API_KEY`): no se serializa ni se
    imprime en repr (FR-009, AC-VT-07). Si falta, el cliente no intenta red
    y devuelve `desconocida` + `VT_NO_DISPONIBLE` (contrato §5).
    """

    tier: TierVT = "public"
    rpm: int = Field(default=TOPE_RPM_PUBLIC, ge=1)
    tope_dia: int = Field(default=TOPE_DIA_PUBLIC, ge=0)
    """0 = sin tope diario."""
    max_por_correo: int = Field(default=MAX_CONSULTAS_POR_CORREO, ge=1)
    upload_unknown: bool = False
    submit_unknown_urls: bool = False
    umbral_maliciosa: int = Field(default=UMBRAL_MALICIOSA, ge=1)
    umbral_sospechosa: int = Field(default=UMBRAL_SOSPECHOSA, ge=1)
    umbral_limpia: int = Field(default=UMBRAL_LIMPIA, ge=0)
    api_key: str | None = Field(default=None, repr=False, exclude=True)

    @classmethod
    def desde_entorno(cls, environ: Mapping[str, str] | None = None) -> ConfigVT:
        """Construye la configuración desde variables de entorno.

        En modo `premium`, si `VT_RPM`/`VT_DAILY` no están definidos se
        aplican los mismos defaults que en `public` (4/min y 500/día): el
        modo premium solo eleva el límite cuando se configura explícitamente
        (clarify 2026-10-27). Valor inválido → `ConfiguracionError` antes de
        consultar (Art. III.9).
        """
        env = os.environ if environ is None else environ
        tier = env.get("VT_TIER", "").strip() or "public"
        if tier not in ("public", "premium"):
            raise ConfiguracionError(f"VT_TIER debe ser 'public' o 'premium': {tier!r}")
        campos: dict[str, Any] = {
            "tier": tier,
            "rpm": _entero(env, "VT_RPM", TOPE_RPM_PUBLIC, minimo=1),
            "tope_dia": _entero(env, "VT_DAILY", TOPE_DIA_PUBLIC, minimo=0),
            "max_por_correo": _entero(
                env, "VT_MAX_POR_CORREO", MAX_CONSULTAS_POR_CORREO, minimo=1
            ),
            "umbral_maliciosa": _entero(env, "VT_UMBRAL_MALICIOSA", UMBRAL_MALICIOSA, minimo=1),
            "umbral_sospechosa": _entero(
                env, "VT_UMBRAL_SOSPECHOSA", UMBRAL_SOSPECHOSA, minimo=1
            ),
            "umbral_limpia": _entero(env, "VT_UMBRAL_LIMPIA", UMBRAL_LIMPIA, minimo=0),
            "upload_unknown": _booleano(env, "VT_UPLOAD_UNKNOWN"),
            "submit_unknown_urls": _booleano(env, "VT_SUBMIT_UNKNOWN_URLS"),
            "api_key": (env.get("VT_API_KEY", "").strip() or None),
        }
        try:
            return cls(**campos)
        except ValidationError as exc:
            raise ConfiguracionError(f"ConfigVT inválida: {exc}") from exc


def _entero(
    env: Mapping[str, str], nombre: str, defecto: int, *, minimo: int
) -> int:
    """Lee un entero del entorno; vacío → default; inválido → error."""
    crudo = env.get(nombre, "").strip()
    if not crudo:
        return defecto
    try:
        valor = int(crudo)
    except ValueError as exc:
        raise ConfiguracionError(f"{nombre} no es un entero: {crudo!r}") from exc
    if valor < minimo:
        raise ConfiguracionError(f"{nombre} debe ser >= {minimo}: {valor}")
    return valor


def _booleano(env: Mapping[str, str], nombre: str) -> bool:
    """`"true"/"1"/"yes"` (case-insensitive) → True; cualquier otra cosa → False."""
    return env.get(nombre, "").strip().lower() in _TRUE
