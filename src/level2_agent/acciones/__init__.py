"""Ejecutor de acciones idempotentes en Gmail y Jira (spec 010, M08).

API pública:
    ejecutar_acciones, EntradaAcciones, ResultadoAccion, ResultadoAcciones,
    Accion, GmailAdapter, JiraAdapter, ResultadoJira, resolver_acciones,
    calcular_huella, sanear_texto_jira, constantes
"""

from __future__ import annotations

from .ejecutor import ejecutar_acciones
from .gmail_adapter import GmailAdapter
from .huella import calcular_huella
from .jira_adapter import JiraAdapter, ResultadoJira, sanear_texto_jira
from .modelos import (
    DRY_RUN_DEFAULT,
    ETIQUETA_PHISHING,
    ETIQUETA_REVISAR,
    HUELLA_LONGITUD,
    JIRA_PROYECTO,
    JIRA_TIPO_TICKET,
    MAX_CHARS_DESCRIPCION_JIRA,
    MAX_CHARS_SUMMARY_JIRA,
    Accion,
    EntradaAcciones,
    ResultadoAccion,
    ResultadoAcciones,
)
from .tabla import resolver_acciones

__all__ = [
    "DRY_RUN_DEFAULT",
    "ETIQUETA_PHISHING",
    "ETIQUETA_REVISAR",
    "HUELLA_LONGITUD",
    "JIRA_PROYECTO",
    "JIRA_TIPO_TICKET",
    "MAX_CHARS_DESCRIPCION_JIRA",
    "MAX_CHARS_SUMMARY_JIRA",
    "Accion",
    "EntradaAcciones",
    "GmailAdapter",
    "JiraAdapter",
    "ResultadoAccion",
    "ResultadoAcciones",
    "ResultadoJira",
    "calcular_huella",
    "ejecutar_acciones",
    "resolver_acciones",
    "sanear_texto_jira",
]
