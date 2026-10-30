"""AC-PER-03: métricas sobre datos de siembra dan exactamente
total 100; 55/15/30 por veredicto y 60,0 % sin modelo (FR-006)."""

from __future__ import annotations

from datetime import datetime, timezone

from src.level2_agent.persistencia.metricas import calcular_metricas
from src.level2_agent.persistencia.repositorio import RepositorioDoble
from src.level2_agent.persistencia.siembra import sembrar_datos


def test_metricas_siembra_total() -> None:
    """Siembra 100 → métricas.total == 100."""
    repo = RepositorioDoble()
    n = sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    assert n == 100

    docs = repo.listar({"origen": "siembra"})
    # Reconstruir AnalisisPersistido desde dicts
    from src.level2_agent.persistencia.modelos import AnalisisPersistido
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    m = calcular_metricas(analisis)
    assert m.total == 100


def test_metricas_siembra_por_veredicto() -> None:
    """Siembra → 55 sin_indicadores, 15 sospechoso, 30 malicioso."""
    repo = RepositorioDoble()
    sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    docs = repo.listar({"origen": "siembra"})
    from src.level2_agent.persistencia.modelos import AnalisisPersistido
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    m = calcular_metricas(analisis)
    assert m.por_veredicto.get("sin_indicadores", 0) == 55
    assert m.por_veredicto.get("sospechoso", 0) == 15
    assert m.por_veredicto.get("malicioso", 0) == 30


def test_metricas_siembra_pct_sin_modelo() -> None:
    """Siembra → 60% resuelto sin modelo (heurística + reglas)."""
    repo = RepositorioDoble()
    sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    docs = repo.listar({"origen": "siembra"})
    from src.level2_agent.persistencia.modelos import AnalisisPersistido
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    m = calcular_metricas(analisis)
    assert abs(m.pct_sin_modelo - 60.0) < 0.01
