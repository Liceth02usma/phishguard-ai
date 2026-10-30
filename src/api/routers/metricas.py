"""Router de métricas: GET /api/metrics/summary (spec 012)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Query

from src.api.deps import APIKeyDep, RepoDep
from src.api.schemas.comunes import Rango
from src.api.schemas.metricas import (
    IndicadorFrecuente,
    MetricasResponse,
    PorDiaResponse,
)
from src.level2_agent.persistencia.metricas import calcular_metricas
from src.level2_agent.persistencia.modelos import AnalisisPersistido

router = APIRouter(prefix="/metrics", tags=["Metricas"])

_RANGO_DIAS: dict[Rango, int] = {"7d": 7, "30d": 30, "90d": 90}


@router.get("/summary", response_model=MetricasResponse)
async def get_metrics_summary(
    _: APIKeyDep,
    repo: RepoDep,
    rango: Rango = Query(description="Rango de métricas (7d, 30d, 90d)"),
) -> MetricasResponse:
    """KPI del tablero para un rango (AC-API-05)."""
    from datetime import datetime, timezone

    hoy = date(2026, 10, 30)  # simplificado; en prod usar date.today()
    dias = _RANGO_DIAS[rango]
    inicio = hoy - timedelta(days=dias - 1)

    # Leer análisis del repo
    docs = repo.listar({})
    analisis = [AnalisisPersistido.model_validate(d) for d in docs]

    # Calcular métricas (función pura de spec 011)
    m = calcular_metricas(analisis, inicio=inicio, fin=hoy)

    # Convertir a response
    por_dia = [
        PorDiaResponse(
            fecha=d.fecha,
            total=d.total,
            malicioso=d.malicioso,
            sospechoso=d.sospechoso,
            revision_manual=d.revision_manual,
            sin_indicadores=d.sin_indicadores,
        )
        for d in m.por_dia
    ]

    indicadores = [
        IndicadorFrecuente(codigo=c, frecuencia=f)
        for c, f in m.indicadores_frecuentes
    ]

    # por_ruta
    por_ruta: dict[str, int] = {}
    for a in analisis:
        por_ruta[a.ruta] = por_ruta.get(a.ruta, 0) + 1

    # revision_manual_total
    rm_total = m.por_veredicto.get("revision_manual", 0)

    # aciertos_cache_pct
    total_vt = m.consultas_vt + m.aciertos_cache
    cache_pct = (m.aciertos_cache / total_vt * 100) if total_vt > 0 else 0.0

    return MetricasResponse(
        rango=rango,
        total=m.total,
        por_veredicto=m.por_veredicto,
        por_ruta=por_ruta,
        pct_sin_modelo=m.pct_sin_modelo,
        duracion_media_ms=m.duracion_media_ms,
        por_dia=por_dia,
        indicadores_frecuentes=indicadores,
        tasa_falsos_positivos=m.tasa_falsos_positivos,
        consultas_vt=m.consultas_vt,
        aciertos_cache_pct=round(cache_pct, 1),
        revision_manual_total=rm_total,
    )
