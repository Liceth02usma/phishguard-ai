"""Configuración del análisis de URLs (spec 004, research D8/D12).

Listas configurables vía `.env` con defaults documentados. Los valores
numéricos que fijan la spec/plan (5 saltos, 5 s) NO son configurables sin
decisión: llegan como constantes de `modelos.py` (Art. VI.2).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Final

from pydantic import BaseModel, Field
from src.level2_agent.analisis_urls.modelos import TIMEOUT_URL_SEGUNDOS, TOPE_SALTOS
from src.level3_logic.genetic_logic import SHORTENERS


class ConfiguracionError(ValueError):
    """Configuración inválida detectada antes de analizar (Art. III.9)."""


# Defaults grounded: acortadores = SHORTENERS existentes en genetic_logic (D8);
# parámetros sensibles = los 7 literales de FR-007 (D12); tracking/TLD/umbral =
# propuestas documentadas en research D8, marcadas [VERIFICAR] en quickstart.
_ACORTADORES_SEMILLA: Final[frozenset[str]] = frozenset(SHORTENERS)
_TLDS_RIESGO_DEFECTO: Final[frozenset[str]] = frozenset(
    {"zip", "mov", "tk", "ml", "cf", "ga", "gq"}
)
_PARAMETROS_TRACKING_DEFECTO: Final[frozenset[str]] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "msclkid",
        "igshid",
        "mc_eid",
        "mc_cid",
        "ref",
        "ref_src",
    }
)
_PARAMETROS_SENSIBLES_FR007: Final[frozenset[str]] = frozenset(
    {"token", "key", "session", "email", "user", "code", "password"}
)
_UMBRAL_SUBDOMINIOS_DEFECTO: Final[int] = 4


def _lista(valor: str) -> frozenset[str]:
    """Divide una lista por coma, normaliza a minúsculas y descarta vacíos."""
    return frozenset(parte.strip().lower() for parte in valor.split(",") if parte.strip())


class ConfigURLs(BaseModel):
    """Configuración inyectable del análisis de URLs (research D8)."""

    acortadores: frozenset[str] = Field(default=_ACORTADORES_SEMILLA)
    tlds_riesgo: frozenset[str] = Field(default=_TLDS_RIESGO_DEFECTO)
    parametros_tracking: frozenset[str] = Field(default=_PARAMETROS_TRACKING_DEFECTO)
    parametros_sensibles: frozenset[str] = Field(default=_PARAMETROS_SENSIBLES_FR007)
    umbral_subdominios: int = Field(default=_UMBRAL_SUBDOMINIOS_DEFECTO, ge=1)
    tope_saltos: int = Field(default=TOPE_SALTOS, ge=1)
    timeout_url: float = Field(default=TIMEOUT_URL_SEGUNDOS, gt=0)

    @classmethod
    def desde_entorno(cls, environ: Mapping[str, str] | None = None) -> ConfigURLs:
        """Lee `ACORTADORES`, `TLD_RIESGO`, `PARAMETROS_TRACKING`,
        `PARAMETROS_SENSIBLES` y `URL_SUBDOMINIOS_MAX` (separadas por coma).

        Valor vacío o ausente → default documentado; umbral no entero →
        `ConfiguracionError` antes de analizar (Art. III.9).
        """
        env = os.environ if environ is None else environ
        campos: dict[str, Any] = {}
        variables = {
            "acortadores": "ACORTADORES",
            "tlds_riesgo": "TLD_RIESGO",
            "parametros_tracking": "PARAMETROS_TRACKING",
            "parametros_sensibles": "PARAMETROS_SENSIBLES",
        }
        for campo, variable in variables.items():
            crudo = env.get(variable, "")
            if crudo.strip():
                campos[campo] = _lista(crudo)
        umbral = env.get("URL_SUBDOMINIOS_MAX", "").strip()
        if umbral:
            try:
                campos["umbral_subdominios"] = int(umbral)
            except ValueError as exc:
                raise ConfiguracionError(
                    f"URL_SUBDOMINIOS_MAX no es un entero: {umbral!r}"
                ) from exc
        return cls(**campos)
