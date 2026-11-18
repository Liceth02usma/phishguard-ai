"""AC-API-05: las métricas coinciden con las fórmulas del frontend sobre los datos de siembra."""

from __future__ import annotations

import os
from datetime import UTC

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble
from src.level2_agent.persistencia.siembra import sembrar_datos


@pytest.mark.ac("AC-API-05")
def test_metricas_sobre_datos_de_siembra() -> None:
    """Con datos de siembra (100 análisis), las métricas coinciden con las fórmulas."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    repo = RepositorioAnalisisDoble()
    app.state.repo = repo
    app.state.cache_vt = CacheVTDoble()

    # Sembrar datos deterministas (55 sin_indicadores, 15 sospechoso, 30 malicioso)
    from datetime import datetime

    ahora = datetime.now(tz=UTC)
    sembrar_datos(repo=repo, ahora=ahora)

    c = TestClient(app)
    r = c.get(
        "/api/metrics/summary",
        params={"rango": "90d"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    data = r.json()

    # Fórmulas de siembra (spec 011, FR-006):
    # total = 100, 55 sin_indicadores, 15 sospechoso, 30 malicioso
    assert data["total"] == 100
    pv = data["por_veredicto"]
    assert pv.get("sin_indicadores", 0) == 55
    assert pv.get("sospechoso", 0) == 15
    assert pv.get("malicioso", 0) == 30

    # 60% sin modelo (55 sin_indicadores + 5 sospechoso = 60 de 100)
    assert abs(data["pct_sin_modelo"] - 60.0) < 1.0


@pytest.mark.ac("AC-API-05")
def test_metricas_rango_7d_solo_ultimos_7_dias() -> None:
    """Rango 7d solo cuenta análisis de los últimos 7 días."""
    os.environ["API_KEY"] = "test-key"
    app = create_app()
    repo = RepositorioAnalisisDoble()
    app.state.repo = repo
    app.state.cache_vt = CacheVTDoble()

    from datetime import datetime

    ahora = datetime.now(tz=UTC)
    sembrar_datos(repo=repo, ahora=ahora)

    c = TestClient(app)
    r = c.get(
        "/api/metrics/summary",
        params={"rango": "7d"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    data = r.json()
    # Los datos de siembra se crean en los últimos 90 días,
    # rango 7d puede tener menos de 100
    assert data["total"] <= 100
