"""Schemas comunes de la API (spec 012).

Enums, paginación, tipos compartidos.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Enums (alineados con spec 008 + contrato OpenAPI) ---

Veredicto = Literal["malicioso", "sospechoso", "revision_manual", "sin_indicadores"]
Severidad = Literal["Critico", "Alto", "Medio", "Bajo"]
Ruta = Literal["reglas", "heuristica", "ia"]
ModoAPI = Literal["pegar", "eml", "muestra", "gmail"]
OrigenAPI = Literal["gmail", "api", "seed"]
Reputacion = Literal["maliciosa", "sospechosa", "limpia", "desconocida"]
Feedback = Literal["confirmado", "falso_positivo"]
Rango = Literal["7d", "30d", "90d"]
AuthResult = Literal[
    "pass", "fail", "none", "neutral", "softfail",
    "permerror", "temperror", "desconocido",
]

# --- Paginación ---


class Paginacion(BaseModel):
    """Envoltorio de paginación [PROPUESTA]."""

    pagina: int = Field(ge=1, default=1, description="Página actual (base 1)")
    limite: int = Field(
        ge=1, le=50, default=50, description="Tamaño de página (≤ 50)"
    )
    total: int = Field(ge=0, description="Total de resultados")


class OrdenAnalisis(BaseModel):
    """Parámetros de orden [VERIFICAR]."""

    campo: str = Field(default="creado_en", description="Campo de orden")
    direccion: Literal["asc", "desc"] = Field(
        default="desc", description="Dirección"
    )
