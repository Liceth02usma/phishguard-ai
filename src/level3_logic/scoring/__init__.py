"""Scoring con clasificador lineal y banderas (spec 007).

API pública:
    calcular_score_final, ScoreFinal, BanderaScoring, ConfigScoring,
    DependenciasScoring, ScoringError, ModeloError
"""

from __future__ import annotations

from .configuracion import ConfigScoring
from .modelos import BanderaScoring, ModeloError, ScoreFinal, ScoringError
from .motor import DependenciasScoring, calcular_score_final

__all__ = [
    "BanderaScoring",
    "ConfigScoring",
    "DependenciasScoring",
    "ModeloError",
    "ScoreFinal",
    "ScoringError",
    "calcular_score_final",
]
