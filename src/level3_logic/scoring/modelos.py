"""Modelos del paquete scoring (spec 007): ScoreFinal, BanderaScoring, errores."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator
from src.level2_agent.banderas.modelos import TOPE_PUNTOS_BANDERAS
from src.level3_logic.modelo import ModeloError


class ScoringError(Exception):
    """Error base del paquete scoring."""


# ModeloError se importa de src.level3_logic.modelo (fuente única)


class BanderaScoring(BaseModel):
    """Bandera de scoring con origen, código y puntos."""

    origen: Literal["cabeceras", "urls", "adjuntos"]
    codigo: str
    puntos: int = 0

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, BanderaScoring):
            return NotImplemented
        return (self.origen, self.codigo) < (other.origen, other.codigo)


class GenImplicado(BaseModel):
    """Gen activo con su característica y peso del modelo."""

    caracteristica: str
    peso: float


class ScoreFinal(BaseModel):
    """Resultado final del scoring: score_clasificador + puntos_banderas.

    Invariante: score_final == min(100, round(score_clasificador + puntos_banderas)).
    """

    score_final: int
    score_clasificador: float
    puntos_banderas: int
    version_modelo: str
    genes_implicados: list[GenImplicado] = []
    banderas: list[BanderaScoring] = []

    @model_validator(mode="after")
    def _validar_invariante(self) -> ScoreFinal:
        esperado = min(100, round(self.score_clasificador + self.puntos_banderas))
        if self.score_final != esperado:
            raise ValueError(
                f"Invariante rota: score_final={self.score_final} != "
                f"min(100, round({self.score_clasificador} + {self.puntos_banderas})) = {esperado}"
            )
        if self.puntos_banderas > TOPE_PUNTOS_BANDERAS:
            raise ValueError(
                f"puntos_banderas={self.puntos_banderas} "
                f"> TOPE_PUNTOS_BANDERAS={TOPE_PUNTOS_BANDERAS}"
            )
        return self
