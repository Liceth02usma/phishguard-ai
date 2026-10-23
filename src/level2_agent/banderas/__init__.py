"""Banderas deterministas de cabeceras y remitente (spec 003, modulo M03).

Producen, para un ``EmailData`` normalizado (spec 002), el conjunto de banderas
del catalogo 5.1 con codigo, severidad, puntos y detalle, sin IA:

    from src.level2_agent.banderas import evaluar_banderas
"""

from __future__ import annotations

from .configuracion import ConfigBanderas, ConfiguracionError
from .modelos import (
    CATALOGO_BANDERAS,
    TOPE_PUNTOS_BANDERAS,
    BanderaActivada,
    EstadosAutenticacion,
    ResultadoBanderas,
)
from .motor import evaluar_banderas
from .rdap import ClienteRDAP

__all__ = [
    "CATALOGO_BANDERAS",
    "TOPE_PUNTOS_BANDERAS",
    "BanderaActivada",
    "ClienteRDAP",
    "ConfigBanderas",
    "ConfiguracionError",
    "EstadosAutenticacion",
    "ResultadoBanderas",
    "evaluar_banderas",
]
