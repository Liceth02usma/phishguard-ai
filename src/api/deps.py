"""Dependency injection para la API (spec 012).

verificar_api_key(): autenticación por X-API-Key.
get_repo(): repositorio de análisis (spec 011).
get_cache_vt(): caché de VirusTotal.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from .config import get_api_key
from .errors import NoAutenticadoError
from .persistence_repos import RepositorioAnalisisDoble, CacheVTDoble


async def verificar_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """Verifica la cabecera X-API-Key (AC-API-07).

    Retorna la key si es válida, lanza 401 si no.
    """
    expected = get_api_key()
    if not expected:
        # Sin key configurada → permitir (desarrollo)
        return x_api_key or "dev"
    if x_api_key != expected:
        raise NoAutenticadoError()
    return x_api_key


# --- Dependencias de repositorio (simulables en tests) ---


def get_repo(request: Request) -> RepositorioAnalisisDoble:
    """Obtiene el repositorio de análisis desde app.state."""
    return getattr(
        request.app.state, "repo", RepositorioAnalisisDoble()
    )


def get_cache_vt(request: Request) -> CacheVTDoble:
    """Obtiene la caché VT desde app.state."""
    return getattr(
        request.app.state, "cache_vt", CacheVTDoble()
    )


# --- Tipo alias para inyección ---

APIKeyDep = Annotated[str, Depends(verificar_api_key)]
RepoDep = Annotated[RepositorioAnalisisDoble, Depends(get_repo)]
CacheVTDep = Annotated[CacheVTDoble, Depends(get_cache_vt)]
