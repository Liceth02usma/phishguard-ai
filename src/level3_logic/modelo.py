"""Módulo modelo: carga y validación del clasificador lineal (spec 007).

Lee data/modelo/clasificador_v1.json con coeficientes e intercepto de una
regresión logística entrenada offline. Producto punto en Python puro (0 deps runtime).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, model_validator

from src.level3_logic.genetic_logic import MAPEO_INDICES

PROYECTO = Path(__file__).resolve().parent.parent.parent
RUTA_POR_DEFECTO = PROYECTO / "data" / "modelo" / "clasificador_v1.json"

# --- Excepciones ---


class ModeloError(Exception):
    """Error al cargar o validar el modelo del clasificador."""


# --- Modelos Pydantic ---


class Hiperparametros(BaseModel):
    solver: str
    C: float
    max_iter: int
    random_state: int


class MetricasEntrenamiento(BaseModel):
    accuracy: float
    recall: float
    f1: float


class ClasificadorLineal(BaseModel):
    """Schema del archivo data/modelo/clasificador_v1.json.

    Los coeficientes deben tener exactamente las 32 claves de MAPEO_INDICES.
    """

    version: str
    fecha: str
    conjunto_entrenamiento: str
    hiperparametros: Hiperparametros
    metricas_entrenamiento: MetricasEntrenamiento
    intercepto: float
    coeficientes: dict[str, float]

    @model_validator(mode="after")
    def _validar_coeficientes(self) -> ClasificadorLineal:
        esperadas = set(MAPEO_INDICES)
        actuales = set(self.coeficientes.keys())
        faltantes = esperadas - actuales
        sobrantes = actuales - esperadas
        if faltantes or sobrantes:
            partes: list[str] = []
            if faltantes:
                partes.append(f"claves faltantes: {sorted(faltantes)}")
            if sobrantes:
                partes.append(f"claves sobrantes: {sorted(sobrantes)}")
            raise ValueError(f"coeficientes inválidos — {'; '.join(partes)}")
        return self


# --- Cache de proceso ---

_cache_modelo: ClasificadorLineal | None = None
_cache_ruta: Path | None = None


# --- API pública ---


def cargar_modelo(ruta: Path | None = None) -> ClasificadorLineal:
    """Carga el modelo desde JSON con cache de proceso.

    Args:
        ruta: ruta al archivo JSON. Default: data/modelo/clasificador_v1.json.

    Returns:
        ClasificadorLineal validado.

    Raises:
        ModeloError: si el archivo no existe, es ilegible o no valida.
    """
    global _cache_modelo, _cache_ruta  # noqa: PLW0603
    ruta_resuelta = ruta or RUTA_POR_DEFECTO
    if _cache_modelo is not None and _cache_ruta == ruta_resuelta:
        return _cache_modelo

    if not ruta_resuelta.exists():
        raise ModeloError(f"Archivo de modelo no encontrado: {ruta_resuelta}")

    try:
        texto = ruta_resuelta.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModeloError(f"No se pudo leer el archivo de modelo: {exc}") from exc

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ModeloError(f"JSON inválido en archivo de modelo: {exc}") from exc

    try:
        modelo = ClasificadorLineal.model_validate(datos)
    except Exception as exc:
        raise ModeloError(f"Schema inválido en archivo de modelo: {exc}") from exc

    _cache_modelo = modelo
    _cache_ruta = ruta_resuelta
    return modelo


def predecir_probabilidad(modelo: ClasificadorLineal, genes: Sequence[int]) -> float:
    """σ(Σ wᵢ·geneᵢ + b) — producto punto + sigmoide en Python puro.

    Args:
        modelo: clasificador con coeficientes e intercepto.
        genes: secuencia de 32 valores (0 o 1).

    Returns:
        Probabilidad en [0, 1].
    """
    z = modelo.intercepto
    for nombre, valor in zip(MAPEO_INDICES, genes):
        z += modelo.coeficientes.get(nombre, 0.0) * valor
    # Sigmoide numéricamente estable
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def invalidate_cache() -> None:
    """Invalida el cache de modelo (para pruebas)."""
    global _cache_modelo, _cache_ruta  # noqa: PLW0603
    _cache_modelo = None
    _cache_ruta = None
