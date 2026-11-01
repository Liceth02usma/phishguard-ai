"""Modelos de datos del ejecutor de acciones (spec 010, M08).

EntradaAcciones agrupa veredicto + datos del correo.
ResultadoAccion registra una acción individual.
ResultadoAcciones es la salida del orquestador.
Accion enumera las acciones posibles.
ResultadoJira es la salida del adapter Jira.

Constantes y límites son LITERALES de M08 (Art. VI.2).
"""

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from src.level2_agent.models import PhishingReport

# --- Constantes de configuración (Art. III.6: sin números mágicos) ---

ETIQUETA_PHISHING: str = "Phishing Alertas"
"""Label de Gmail para correos maliciosos (ya existente en gmail_reader.py)."""

ETIQUETA_REVISAR: str = "Revisar Seguridad"
"""Label de Gmail para correos sospechosos o que requieren revisión."""

DRY_RUN_DEFAULT: bool = True
"""DRY_RUN activo por defecto (Art. V.2, FR-002)."""

MAX_CHARS_DESCRIPCION_JIRA: int = 3000
"""Límite de descripción del ticket Jira (AC-ACT-04)."""

MAX_CHARS_SUMMARY_JIRA: int = 190
"""Límite de summary del ticket Jira (ya existente en jira_integration.py)."""

HUELLA_LONGITUD: int = 16
"""Longitud de la huella de campaña en hex (D6)."""

JIRA_PROYECTO: str = os.environ.get("JIRA_PROYECTO", "SCRUM")
"""Proyecto Jira (configurable via env var, default SCRUM)."""

JIRA_TIPO_TICKET: str = os.environ.get("JIRA_TIPO_TICKET", "Tarea")
"""Tipo de issue Jira (configurable via env var, default Tarea según n8n)."""

# --- Tipos literales ---

Veredicto = Literal["malicioso", "sospechoso", "revision_manual", "sin_indicadores"]
NivelSeveridad = Literal["Critico", "Alto", "Medio", "Bajo"]
Destino = Literal["gmail", "jira"]
Motivo = Literal["exito", "dry_run", "idempotencia", "error_jira", "error_gmail"]
Origen = Literal["gmail", "api"]


# --- Accion enum (FR-001, D3) ---


class Accion(Enum):
    """Acciones posibles según la tabla de mapeo veredicto→acciones."""

    ETIQUETAR_PHISHING = "etiquetar_phishing"
    ETIQUETAR_REVISAR = "etiquetar_revisar"
    ARCHIVAR = "archivar"
    MARCAR_LEIDO = "marcar_leido"
    CREAR_TICKET = "crear_ticket"
    CREAR_TICKET_BAJA = "crear_ticket_baja"


# --- Modelos Pydantic (Art. III.4) ---


class EntradaAcciones(BaseModel):
    """Entrada del ejecutor de acciones: veredicto + datos del correo."""

    veredicto: Veredicto = Field(description="Veredicto del motor de decisión (spec 008)")
    nivel_severidad: NivelSeveridad = Field(
        description="Nivel de severidad del veredicto"
    )
    message_id: str = Field(min_length=1, description="ID del mensaje en Gmail")
    remitente: str = Field(description="Dirección del remitente")
    asunto: str = Field(description="Asunto del correo")
    urls: list[str] = Field(default_factory=list, description="URLs del correo")
    reporte: PhishingReport = Field(description="Reporte del análisis")
    origen: Origen = Field(description="Origen del correo: gmail o api")
    html_body: str = Field(
        default="",
        exclude=True,
        repr=False,
        description="HTML del correo (solo memoria, para screenshot HCTI, nunca persistido)",
    )


class ResultadoAccion(BaseModel):
    """Registro de una acción individual ejecutada o simulada."""

    accion: Accion = Field(description="Acción ejecutada")
    destino: Destino = Field(description="Servicio destino: gmail o jira")
    identificador: str = Field(description="msg_id o issue_key")
    ejecutada: bool = Field(description="True si se ejecutó, False si simulacro")
    motivo: Motivo = Field(description="Razón del resultado")
    timestamp: datetime = Field(description="Momento de la acción")
    detalle: str | None = Field(
        default=None, description="Info adicional (issue_key, error msg)"
    )


class ResultadoAcciones(BaseModel):
    """Salida del ejecutor: lista de acciones + resumen."""

    acciones: list[ResultadoAccion] = Field(
        default_factory=list, description="Lista de acciones ejecutadas/simuladas"
    )
    huella_campaña: str | None = Field(
        default=None, description="Huella calculada para deduplicación"
    )
    ticket_key: str | None = Field(
        default=None, description="Issue key de Jira (si se creó/vinculó)"
    )
    procesado: bool = Field(
        default=False, description="True si se registró para idempotencia"
    )


class ResultadoJira(BaseModel):
    """Salida del adapter Jira."""

    exito: bool = Field(description="True si la operación fue exitosa")
    issue_key: str | None = Field(default=None, description="Key del issue creado")
    url: str | None = Field(default=None, description="URL del issue en Jira")
    error: str | None = Field(default=None, description="Mensaje de error si falló")
