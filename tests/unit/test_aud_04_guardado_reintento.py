"""Auditoría AUD-03: reintento con backoff en `guardar_analisis`.

Antes del fix, un fallo transitorio de MongoDB ("No primary available for
writes", observado en producción) perdía el análisis silenciosamente con
solo un WARNING. Ahora `guardar_analisis` reintenta con backoff exponencial
y solo propaga la excepción tras agotar los intentos.
"""

from __future__ import annotations

import pytest

from dobles_persistencia import entrada_persistido_ejemplo


class _RepoFallido:
    """Repo que falla las primeras `fallos` veces y luego guarda."""

    def __init__(self, fallos: int) -> None:
        self.fallos = fallos
        self.intentos = 0

    def guardar(self, doc: dict[str, object]) -> str:
        self.intentos += 1
        if self.intentos <= self.fallos:
            raise RuntimeError("Mongo sin primary (doble de auditoría)")
        return str(doc.get("message_id", "ok"))

    def buscar(self, message_id: str) -> dict[str, object] | None:  # noqa: ARG002
        return None

    def listar(self, filtro: dict[str, object] | None = None) -> list[dict[str, object]]:  # noqa: ARG002
        return []

    def borrar(self, message_id: str) -> bool:  # noqa: ARG002
        return False

    def contar(self, filtro: dict[str, object] | None = None) -> int:  # noqa: ARG002
        return 0


def test_reintento_hasta_exitoso() -> None:
    """Fallo transitorio → reintenta y guarda sin perder el análisis."""
    from src.level2_agent.persistencia.guardado import guardar_analisis

    repo = _RepoFallido(fallos=2)
    esperas: list[float] = []
    analisis = entrada_persistido_ejemplo()

    msg_id = guardar_analisis(
        analisis, repo=repo, reintentos=3, dormir=esperas.append
    )

    assert repo.intentos == 3
    assert msg_id  # se guardó en el tercer intento
    # Backoff exponencial: 0.5s tras el 1er fallo, 1s tras el 2º.
    assert esperas == [0.5, 1.0]


def test_reintento_agota_y_propaga() -> None:
    """Fallo persistente → tras agotar reintentos, propaga la excepción."""
    from src.level2_agent.persistencia.guardado import guardar_analisis

    repo = _RepoFallido(fallos=99)
    esperas: list[float] = []
    analisis = entrada_persistido_ejemplo()

    with pytest.raises(RuntimeError, match="Mongo sin primary"):
        guardar_analisis(analisis, repo=repo, reintentos=3, dormir=esperas.append)

    assert repo.intentos == 3
    assert len(esperas) == 2  # no duerme tras el último intento


def test_sin_reintento_en_repo_sano() -> None:
    """Repo sano → un solo intento, cero esperas (sin overhead)."""
    from src.level2_agent.persistencia.guardado import guardar_analisis

    repo = _RepoFallido(fallos=0)
    esperas: list[float] = []
    analisis = entrada_persistido_ejemplo()

    guardar_analisis(analisis, repo=repo, reintentos=3, dormir=esperas.append)

    assert repo.intentos == 1
    assert esperas == []
