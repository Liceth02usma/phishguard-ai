"""AC-PER-04: por_dia tiene un elemento por cada día del rango,
incluidos los de cero (probar 7, 30 y 90 días y cambio de zona)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from src.level2_agent.persistencia.metricas import calcular_metricas
from src.level2_agent.persistencia.modelos import AnalisisPersistido
from src.level2_agent.persistencia.repositorio import RepositorioDoble
from src.level2_agent.persistencia.siembra import sembrar_datos


def test_por_dia_rango_7_dias() -> None:
    """Rango de 7 días → por_dia tiene 7 elementos."""
    repo = RepositorioDoble()
    sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    docs = repo.listar({"origen": "siembra"})
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    m = calcular_metricas(
        analisis,
        inicio=date(2026, 10, 9),
        fin=date(2026, 10, 15),
    )
    assert len(m.por_dia) == 7


def test_por_dia_rango_30_dias() -> None:
    """Rango de 30 días → por_dia tiene 30 elementos."""
    repo = RepositorioDoble()
    sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    docs = repo.listar({"origen": "siembra"})
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    m = calcular_metricas(
        analisis,
        inicio=date(2026, 9, 16),
        fin=date(2026, 10, 15),
    )
    assert len(m.por_dia) == 30


def test_por_dia_rango_90_dias() -> None:
    """Rango de 90 días → por_dia tiene 90 elementos."""
    repo = RepositorioDoble()
    sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    docs = repo.listar({"origen": "siembra"})
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    m = calcular_metricas(
        analisis,
        inicio=date(2026, 7, 17),
        fin=date(2026, 10, 14),
    )
    assert len(m.por_dia) == 90


def test_por_dia_dias_en_cero() -> None:
    """Días sin análisis tienen total=0."""
    repo = RepositorioDoble()
    sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    docs = repo.listar({"origen": "siembra"})
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    # Rango amplio que incluye días sin datos
    m = calcular_metricas(
        analisis,
        inicio=date(2026, 1, 1),
        fin=date(2026, 1, 7),
    )
    assert len(m.por_dia) == 7
    # Enero no tiene datos de siembra (siembra es octubre)
    assert all(d.total == 0 for d in m.por_dia)


def test_por_dia_cambio_zona_horaria() -> None:
    """Cambio de zona horaria puede cambiar la agrupación por día."""
    repo = RepositorioDoble()
    sembrar_datos(repo=repo, ahora=datetime(2026, 10, 15, tzinfo=timezone.utc))
    docs = repo.listar({"origen": "siembra"})
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    m_bog = calcular_metricas(analisis, tz="America/Bogota")
    m_utc = calcular_metricas(analisis, tz="UTC")

    # Ambas tienen por_dia no vacío
    assert len(m_bog.por_dia) > 0
    assert len(m_utc.por_dia) > 0
    # La agrupación puede diferir por zona horaria
    # (no verificamos desigualdad ya que puede coincidir)
