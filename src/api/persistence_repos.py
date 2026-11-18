"""Adapters thin para repositorios de spec 011.

Re-exporta los Protocol y Dobles para uso de la API.
En producción, usa RepositorioReal; en tests, RepositorioAnalisisDoble.
"""

from __future__ import annotations

from src.level2_agent.persistencia.repositorio import (
    CacheVTDoble,
    CacheVTReal,
    RepositorioAnalisis,
    RepositorioCacheVT,
    RepositorioReal,
)
from src.level2_agent.persistencia.repositorio import (
    RepositorioDoble as RepositorioAnalisisDoble,
)

__all__ = [
    "CacheVTDoble",
    "CacheVTReal",
    "RepositorioAnalisis",
    "RepositorioAnalisisDoble",
    "RepositorioCacheVT",
    "RepositorioReal",
]
