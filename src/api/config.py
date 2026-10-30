"""Configuración de la API REST (spec 012, M14).

Settings cargadas desde variables de entorno.
Constantes de rate limit, CSV, paginación, etc.
"""

from __future__ import annotations

import os
from typing import Final

# --- API Key ---
API_KEY_ENV: str = "API_KEY"
"""Variable de entorno para la clave de la API (Art. V.8)."""

# --- Rate limiting ---
RATE_LIMIT_POR_MINUTO: Final[int] = 30
"""FR-003: 30 análisis por minuto por clave e IP."""

# --- CSV ---
CSV_MAX_FILAS: Final[int] = 5000
"""FR-004: máximo filas en exportación CSV."""

CSV_BOM: Final[str] = "\ufeff"
"""BOM UTF-8 para CSV."""

CSV_PREFIJOS_PELIGROSOS: Final[tuple[str, ...]] = ("=", "+", "-", "@")
"""Prefijos que indican inyección de fórmula (CWE-1236)."""

# --- Multipart ---
MULTIPART_MAX_MB: Final[int] = 25
"""FR-001: máximo tamaño de archivo EML."""

MULTIPART_MAX_BYTES: Final[int] = MULTIPART_MAX_MB * 1024 * 1024

# --- Paginación ---
LIMITE_PAGINACION_MAX: Final[int] = 50
"""FR-001: máximo por página."""

LIMITE_PAGINACION_DEFAULT: Final[int] = 50
"""Default por página."""

# --- API ---
API_PREFIX: Final[str] = "/api"
"""Prefijo de rutas."""

# --- CORS ---
CORS_ORIGINS_DEFAULT: Final[list[str]] = []
"""Orígenes CORS por defecto (vacío = sin CORS)."""


def get_api_key() -> str:
    """Lee la API key desde el entorno."""
    return os.environ.get(API_KEY_ENV, "")


def get_cors_origins() -> list[str]:
    """Lee orígenes CORS desde el entorno (comma-separated)."""
    val = os.environ.get("CORS_ORIGINS", "")
    if not val:
        return list(CORS_ORIGINS_DEFAULT)
    return [o.strip() for o in val.split(",") if o.strip()]
