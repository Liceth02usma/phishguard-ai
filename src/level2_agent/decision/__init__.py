"""Motor de decisión determinista (spec 008, M09).

API pública:
    evaluar_veredicto, EntradaMotor, VeredictoMotor, VerificacionIncompleta,
    ReglaAplicada, UMBRAL_BAJO, UMBRAL_ALTO, Veredicto, NivelSeveridad, Ruta,
    IdRegla, TipoVerificacion, SEVERIDAD_REGLA, DESCRIPCION_REGLA
"""

from __future__ import annotations

from .modelos import (
    DESCRIPCION_REGLA,
    SEVERIDAD_REGLA,
    UMBRAL_ALTO,
    UMBRAL_BAJO,
    EntradaMotor,
    IdRegla,
    NivelSeveridad,
    ReglaAplicada,
    Ruta,
    TipoVerificacion,
    Veredicto,
    VeredictoMotor,
    VerificacionIncompleta,
)
from .motor import evaluar_veredicto

__all__ = [
    "DESCRIPCION_REGLA",
    "SEVERIDAD_REGLA",
    "UMBRAL_ALTO",
    "UMBRAL_BAJO",
    "EntradaMotor",
    "IdRegla",
    "NivelSeveridad",
    "ReglaAplicada",
    "Ruta",
    "TipoVerificacion",
    "Veredicto",
    "VeredictoMotor",
    "VerificacionIncompleta",
    "evaluar_veredicto",
]
