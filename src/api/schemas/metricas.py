"""Schemas de métricas (spec 012)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from .comunes import Rango


class PorDiaResponse(BaseModel):
    """Un día del desglose por día."""

    fecha: date = Field(description="Fecha del día")
    total: int = Field(ge=0, description="Total del día")
    malicioso: int = Field(default=0, ge=0)
    sospechoso: int = Field(default=0, ge=0)
    revision_manual: int = Field(default=0, ge=0)
    sin_indicadores: int = Field(default=0, ge=0)


class IndicadorFrecuente(BaseModel):
    """Indicador frecuente."""

    codigo: str = Field(description="Código")
    descripcion: str = Field(default="", description="Descripción")
    frecuencia: int = Field(ge=0, description="Frecuencia")


class MetricasResponse(BaseModel):
    """Respuesta de GET /metrics/summary."""

    rango: Rango = Field(description="Rango de las métricas")
    total: int = Field(ge=0, description="Total análisis")
    por_veredicto: dict[str, int] = Field(
        default_factory=dict, description="Conteo por veredicto"
    )
    por_ruta: dict[str, int] = Field(
        default_factory=dict, description="Conteo por ruta"
    )
    pct_sin_modelo: float = Field(
        ge=0.0, le=100.0, description="% sin modelo"
    )
    duracion_media_ms: float = Field(ge=0.0, description="Duración media")
    por_dia: list[PorDiaResponse] = Field(
        default_factory=list, description="Desglose por día"
    )
    indicadores_frecuentes: list[IndicadorFrecuente] = Field(
        default_factory=list, description="Top 10 indicadores"
    )
    tasa_falsos_positivos: float | None = Field(
        default=None, description="Tasa FP (None sin retroalimentación)"
    )
    consultas_vt: int = Field(default=0, ge=0)
    aciertos_cache_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    revision_manual_total: int = Field(default=0, ge=0)
