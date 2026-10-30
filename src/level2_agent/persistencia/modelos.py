"""Modelos de datos de persistencia y métricas (spec 011, M14).

AnalisisPersistido: documento que se guarda en MongoDB.
Metricas: resultado de las agregaciones.
PorDia: un día del desglose por día.
Constantes TTL y de siembra son LITERALES de M14 (Art. VI.2).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# --- Reutilizar tipos del motor de decisión (spec 008) ---
from src.level2_agent.decision.modelos import (
    NivelSeveridad,
    Ruta,
    Veredicto,
)

# --- Tipos literales propios ---

Origen = Literal["gmail", "api", "siembra"]
"""Origen del análisis: poller Gmail, API externa, o datos de siembra."""

Modo = Literal["produccion", "dry_run"]
"""Modo de ejecución de acciones."""

Retroalimentacion = Literal["confirmado", "falso_positivo"]
"""Feedback del usuario sobre el veredicto."""

# --- Constantes de retención (Art. III.6: sin números mágicos) ---

RETENCION_ANALISIS_DIAS: int = 90
"""TTL de la colección analyses (FR-001)."""

RETENCION_FALLIDOS_DIAS: int = 30
"""TTL de la colección analyses_fallidos (FR-001)."""

RETENCION_VT_CACHE_DIAS: int = 7
"""TTL de la colección vt_cache (ya existente, FR-001)."""

RETENCION_VT_CUOTA_DIAS: int = 2
"""TTL de la colección vt_cuota (FR-001)."""

RETENCION_PROCESADOS_DIAS: int = 90
"""TTL de la colección procesados (FR-001)."""

ZONA_HORARIA: str = "America/Bogota"
"""Zona horaria para agrupación por día (FR-004)."""

COLECCION_ANALISIS: str = "analyses"
"""Nombre de la colección de análisis en MongoDB."""

COLECCION_FALLIDOS: str = "analyses_fallidos"
"""Nombre de la colección de análisis fallidos."""

COLECCION_VT_CACHE: str = "vt_cache"
"""Nombre de la colección de caché VT (ya existente)."""

COLECCION_VT_CUOTA: str = "vt_contador"
"""Nombre de la colección de cuota VT (ya existente)."""

# --- Constantes de siembra (FR-006) ---

SIEMBRA_TOTAL: int = 100
"""Total de análisis de siembra."""

SIEMBRA_SIN_INDICADORES: int = 55
"""sin_indicadores en siembra."""

SIEMBRA_SOSPECHOSOS: int = 15
"""sospechosos en siembra."""

SIEMBRA_MALICIOSOS: int = 30
"""maliciosos en siembra."""

SIEMBRA_SIN_MODELO: int = 60
"""Resueltos por heurística (sin IA)."""


# --- Modelos Pydantic (Art. III.4) ---


class AnalisisPersistido(BaseModel):
    """Documento que se guarda en MongoDB phishguard.analyses.

    Invariantes:
    - I1: nunca contiene htmlBody.
    - I2: nunca contiene contenido de adjuntos.
    """

    message_id: str = Field(min_length=1, description="ID del mensaje en Gmail")
    origen: Origen = Field(description="Origen: gmail, api o siembra")
    modo: Modo = Field(description="Modo: produccion o dry_run")
    fecha: datetime = Field(description="Timestamp del análisis (UTC)")
    duracion_ms: int = Field(ge=0, description="Duración del análisis en ms")
    correo_enmascarado: dict[str, object] = Field(
        description="Correo enmascarado (sin HTML ni adjuntos)"
    )
    score_final: int = Field(ge=0, le=100, description="Score compuesto 0-100")
    ruta: Ruta = Field(description="Cómo se decidió: reglas/heuristica/ia")
    veredicto: Veredicto = Field(description="Veredicto del motor de decisión")
    nivel_severidad: NivelSeveridad = Field(
        description="Nivel de severidad del veredicto"
    )
    banderas: list[str] = Field(
        default_factory=list, description="Banderas activadas"
    )
    reglas_aplicadas: list[str] = Field(
        default_factory=list, description="Reglas R1-R5 que aplicaron"
    )
    autenticacion: dict[str, object] = Field(
        default_factory=dict, description="SPF/DKIM/DMARC"
    )
    urls: list[str] = Field(default_factory=list, description="URLs del correo")
    adjuntos_nombres: list[str] = Field(
        default_factory=list, description="Nombres de adjunto (sin contenido)"
    )
    version_pesos: str = Field(description="Versión del modelo de scoring")
    version_modelo: str = Field(description="Versión del modelo LLM")
    accion: str | None = Field(
        default=None, description="Acción ejecutada (spec 010)"
    )
    retroalimentacion: Retroalimentacion | None = Field(
        default=None, description="Feedback del usuario"
    )
    consultas_vt: int = Field(
        default=0, ge=0, description="Consultas VT realizadas"
    )
    aciertos_cache_vt: int = Field(
        default=0, ge=0, description="Aciertos de caché VT"
    )
    expira_en: datetime = Field(description="Fecha de expiración TTL")


class PorDia(BaseModel):
    """Un día del desglose por día."""

    fecha: date = Field(description="Fecha del día")
    total: int = Field(ge=0, description="Total de análisis del día")
    malicioso: int = Field(ge=0, description="Maliciosos del día")
    sospechoso: int = Field(ge=0, description="Sospechosos del día")
    revision_manual: int = Field(ge=0, description="Revisión manual del día")
    sin_indicadores: int = Field(ge=0, description="Sin indicadores del día")


class Metricas(BaseModel):
    """Resultado de las agregaciones sobre análisis."""

    total: int = Field(ge=0, description="Total de análisis")
    por_veredicto: dict[str, int] = Field(
        default_factory=dict, description="Conteo por veredicto"
    )
    pct_sin_modelo: float = Field(
        ge=0.0, le=100.0, description="% resuelto sin IA"
    )
    duracion_media_ms: float = Field(
        ge=0.0, description="Duración media en ms"
    )
    por_dia: list[PorDia] = Field(
        default_factory=list, description="Desglose por día"
    )
    indicadores_frecuentes: list[tuple[str, int]] = Field(
        default_factory=list, description="Top 10 indicadores más frecuentes"
    )
    tasa_falsos_positivos: float | None = Field(
        default=None,
        description="None si no hay retroalimentación",
    )
    consultas_vt: int = Field(
        default=0, ge=0, description="Total consultas VT"
    )
    aciertos_cache: int = Field(
        default=0, ge=0, description="Total aciertos caché VT"
    )
