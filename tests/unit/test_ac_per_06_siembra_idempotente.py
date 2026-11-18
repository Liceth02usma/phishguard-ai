"""AC-PER-06: ejecutar la siembra dos veces deja exactamente
100 documentos de origen siembra y no toca los de usuario (I4)."""

from __future__ import annotations

from datetime import UTC, datetime

from src.level2_agent.persistencia.guardado import guardar_analisis
from src.level2_agent.persistencia.repositorio import RepositorioDoble
from src.level2_agent.persistencia.siembra import sembrar_datos

from dobles_persistencia import entrada_persistido_ejemplo


def test_siembra_idempotente() -> None:
    """Siembra 2 veces → exactamente 100 docs con origen=siembra."""
    repo = RepositorioDoble()
    ts = datetime(2026, 10, 15, tzinfo=UTC)

    n1 = sembrar_datos(repo=repo, ahora=ts)
    assert n1 == 100
    assert repo.contar({"origen": "siembra"}) == 100

    n2 = sembrar_datos(repo=repo, ahora=ts)
    assert n2 == 100
    assert repo.contar({"origen": "siembra"}) == 100


def test_siembra_no_toca_usuario() -> None:
    """Siembra no elimina documentos de origen gmail/api."""
    repo = RepositorioDoble()

    # Insertar un documento de usuario
    a_user = entrada_persistido_ejemplo(
        message_id="msg_user_001", origen="gmail"
    )
    guardar_analisis(a_user, repo=repo)
    assert repo.buscar("msg_user_001") is not None

    # Ejecutar siembra
    sembrar_datos(
        repo=repo,
        ahora=datetime(2026, 10, 15, tzinfo=UTC),
    )

    # El documento de usuario sigue existiendo
    assert repo.buscar("msg_user_001") is not None
    assert repo.contar({"origen": "gmail"}) == 1
