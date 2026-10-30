"""Agente de IA sin estado (spec 009, M07).

API pública:
    consultar_agente, EntradaAgente, SalidaAgente, ResultadoAgente,
    ModeloLLM, ContadorLLM, LLM_MAX_DIARIO_DEFAULT, LLM_MODELO_DEFAULT,
    LLM_TEMPERATURA, MAX_REINTENTOS, DELIM_CORREO_INICIO, DELIM_CORREO_FIN
"""

from __future__ import annotations

from .contador import ContadorLLM
from .modelos import (
    DELIM_CORREO_FIN,
    DELIM_CORREO_INICIO,
    LLM_MAX_DIARIO_DEFAULT,
    LLM_MODELO_DEFAULT,
    LLM_TEMPERATURA,
    MAX_REINTENTOS,
    EntradaAgente,
    ModeloLLM,
    ResultadoAgente,
    SalidaAgente,
)

__all__ = [
    "DELIM_CORREO_FIN",
    "DELIM_CORREO_INICIO",
    "LLM_MAX_DIARIO_DEFAULT",
    "LLM_MODELO_DEFAULT",
    "LLM_TEMPERATURA",
    "MAX_REINTENTOS",
    "ContadorLLM",
    "EntradaAgente",
    "ModeloLLM",
    "ResultadoAgente",
    "SalidaAgente",
    "consultar_agente",
]

# consultar_agente se importa después para evitar circularidad
from .agente import consultar_agente  # noqa: E402
