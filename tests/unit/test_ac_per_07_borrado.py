"""AC-PER-07: borrar un análisis elimina el documento y su caché
asociada (FR-005)."""

from __future__ import annotations

from src.level2_agent.persistencia.borrado import borrar_analisis
from src.level2_agent.persistencia.guardado import guardar_analisis
from src.level2_agent.persistencia.repositorio import (
    CacheVTDoble,
    RepositorioDoble,
)

from dobles_persistencia import entrada_persistido_ejemplo


def test_borrar_elimina_documento() -> None:
    """borrar_analisis → documento eliminado de analyses."""
    repo = RepositorioDoble()
    a = entrada_persistido_ejemplo(message_id="msg_001")
    guardar_analisis(a, repo=repo)
    assert repo.buscar("msg_001") is not None

    resultado = borrar_analisis("msg_001", repo=repo)
    assert resultado is True
    assert repo.buscar("msg_001") is None


def test_borrar_eliminia_cache_vt() -> None:
    """borrar_analisis → caché VT asociada eliminada."""
    repo = RepositorioDoble()
    cache = CacheVTDoble()
    a = entrada_persistido_ejemplo(message_id="msg_001")
    guardar_analisis(a, repo=repo)

    # Agregar caché VT
    cache.agregar("msg_001", {"hash": "abc123", "veredicto": "malicious"})

    resultado = borrar_analisis("msg_001", repo=repo, cache_vt=cache)
    assert resultado is True
    assert cache.borrar_por_message_id("msg_001") == 0  # ya fue borrado


def test_borrar_no_existente() -> None:
    """borrar_analisis de msg inexistente → False."""
    repo = RepositorioDoble()
    resultado = borrar_analisis("msg_inexistente", repo=repo)
    assert resultado is False
