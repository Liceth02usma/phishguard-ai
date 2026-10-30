"""Persistencia y métricas de análisis (spec 011, M14).

API pública:
    guardar_analisis, calcular_metricas, sembrar_datos, borrar_analisis,
    AnalisisPersistido, Metricas, PorDia,
    RepositorioAnalisis, RepositorioCacheVT,
    RepositorioReal, CacheVTReal,
    RepositorioDoble, CacheVTDoble,
    constantes
"""

from __future__ import annotations

from .borrado import borrar_analisis
from .guardado import guardar_analisis
from .metricas import calcular_metricas
from .modelos import (
    COLECCION_ANALISIS,
    COLECCION_FALLIDOS,
    COLECCION_VT_CACHE,
    RETENCION_ANALISIS_DIAS,
    RETENCION_FALLIDOS_DIAS,
    RETENCION_PROCESADOS_DIAS,
    RETENCION_VT_CACHE_DIAS,
    RETENCION_VT_CUOTA_DIAS,
    SIEMBRA_MALICIOSOS,
    SIEMBRA_SIN_INDICADORES,
    SIEMBRA_SIN_MODELO,
    SIEMBRA_SOSPECHOSOS,
    SIEMBRA_TOTAL,
    ZONA_HORARIA,
    AnalisisPersistido,
    Metricas,
    Modo,
    Origen,
    PorDia,
    Retroalimentacion,
)
from .repositorio import (
    CacheVTDoble,
    CacheVTReal,
    RepositorioAnalisis,
    RepositorioCacheVT,
    RepositorioDoble,
    RepositorioReal,
)
from .siembra import sembrar_datos

__all__ = [
    "COLECCION_ANALISIS",
    "COLECCION_FALLIDOS",
    "COLECCION_VT_CACHE",
    "RETENCION_ANALISIS_DIAS",
    "RETENCION_FALLIDOS_DIAS",
    "RETENCION_PROCESADOS_DIAS",
    "RETENCION_VT_CACHE_DIAS",
    "RETENCION_VT_CUOTA_DIAS",
    "SIEMBRA_MALICIOSOS",
    "SIEMBRA_SIN_INDICADORES",
    "SIEMBRA_SIN_MODELO",
    "SIEMBRA_SOSPECHOSOS",
    "SIEMBRA_TOTAL",
    "ZONA_HORARIA",
    "AnalisisPersistido",
    "CacheVTDoble",
    "CacheVTReal",
    "Metricas",
    "Modo",
    "Origen",
    "PorDia",
    "RepositorioAnalisis",
    "RepositorioCacheVT",
    "RepositorioDoble",
    "RepositorioReal",
    "Retroalimentacion",
    "borrar_analisis",
    "calcular_metricas",
    "guardar_analisis",
    "sembrar_datos",
]
