"""Schemas de análisis (spec 012).

Request models: AnalisisPegarRequest, AnalisisMuestraRequest.
Response models: AnalisisResponse, CorreoResponse, ResultadoResponse, etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .comunes import (
    Feedback,
    ModoAPI,
    OrigenAPI,
    Reputacion,
    Ruta,
    Severidad,
    Veredicto,
)


# --- Request models ---


class AnalisisPegarRequest(BaseModel):
    """POST /analyses modo pegar (JSON)."""

    modo: Literal["pegar"] = Field(description="Modo pegar")
    dry_run: bool = Field(
        default=True,
        description="Simulacro por defecto (Art. V.2)",
    )
    raw: str | None = Field(
        default=None,
        description="Correo MIME en base64 url-safe",
    )
    subject: str | None = Field(default=None, description="Asunto")
    from_: str | None = Field(
        default=None, alias="from", description="Remitente"
    )
    to: str | None = Field(default=None, description="Destinatario")
    text: str | None = Field(default=None, description="Cuerpo texto")
    html: str | None = Field(default=None, description="Cuerpo HTML")
    headers: dict[str, str] | None = Field(
        default=None, description="Cabeceras"
    )
    message_id: str | None = Field(default=None, description="ID del mensaje")

    model_config = {"populate_by_name": True}


class AnalisisMuestraRequest(BaseModel):
    """POST /analyses modo muestra (JSON)."""

    modo: Literal["muestra"] = Field(description="Modo muestra")
    muestra: str = Field(description="ID de la muestra")
    dry_run: bool = Field(default=True, description="Simulacro por defecto")


class AnalisisEmlRequest(BaseModel):
    """POST /analyses modo eml (multipart/form-data).

    El archivo EML se envía como campo 'archivo' en multipart.
    """

    modo: Literal["eml"] = Field(description="Modo eml")
    dry_run: bool = Field(default=True, description="Simulacro por defecto")


# --- Response models ---


class CorreoResponse(BaseModel):
    """Correo enmascarado (siempre PII protegida, Art. V.4)."""

    remitente: str = Field(description="Remitente enmascarado")
    asunto: str = Field(description="Asunto")
    cuerpo_enmascarado: str = Field(
        default="", description="Cuerpo enmascarado"
    )


class IndicadorResponse(BaseModel):
    """Indicador de phishing."""

    codigo: str = Field(description="Código del indicador")
    descripcion: str = Field(description="Descripción humana")
    peso: float = Field(description="Peso del indicador")


class BanderaResponse(BaseModel):
    """Bandera de cabeceras."""

    codigo: str = Field(description="Código de la bandera")
    severidad: str = Field(description="Severidad")
    puntos: int = Field(description="Puntos")
    detalle: str = Field(description="Detalle")


class UrlResponse(BaseModel):
    """URL con reputación."""

    url: str = Field(description="URL")
    reputacion: Reputacion = Field(description="Reputación VT")
    detalle_vt: dict[str, int] | None = Field(
        default=None, description="Stats VT"
    )


class AdjuntoResponse(BaseModel):
    """Adjunto con hash y reputación."""

    nombre: str = Field(description="Nombre del archivo")
    tipo_real: str | None = Field(default=None, description="Tipo MIME real")
    sha256: str = Field(description="SHA-256 del archivo")
    tamano: int = Field(description="Tamaño en bytes")
    reputacion: Reputacion = Field(description="Reputación VT")


class TicketResponse(BaseModel):
    """Ticket Jira vinculado."""

    clave: str = Field(description="Key del ticket")
    url: str = Field(description="URL del ticket")


class AutenticacionResponse(BaseModel):
    """Estados SPF/DKIM/DMARC."""

    spf: str = Field(description="Resultado SPF")
    dkim: str = Field(description="Resultado DKIM")
    dmarc: str = Field(description="Resultado DMARC")


class ResultadoResponse(BaseModel):
    """Resultado del análisis."""

    score: int = Field(ge=0, le=100, description="Score final 0-100")
    score_genetico: int | None = Field(default=None, description="Score genético")
    ruta: Ruta = Field(description="Ruta de decisión")
    es_phishing: bool = Field(description="Compatibilidad legado")
    veredicto: Veredicto = Field(description="Veredicto canónico")
    nivel_severidad: Severidad = Field(description="Nivel de severidad")
    resumen: str = Field(description="Resumen")
    analisis_tecnico: str = Field(default="", description="Análisis técnico")
    justificacion_veredicto: str = Field(
        default="", description="Justificación"
    )
    indicadores: list[IndicadorResponse] = Field(
        default_factory=list, description="Indicadores"
    )
    banderas: list[BanderaResponse] = Field(
        default_factory=list, description="Banderas"
    )
    reglas_aplicadas: list[str] = Field(
        default_factory=list, description="Reglas R1-R5"
    )
    verificaciones_incompletas: list[str] = Field(
        default_factory=list, description="Verificaciones incompletas"
    )
    autenticacion: AutenticacionResponse = Field(
        default_factory=lambda: AutenticacionResponse(
            spf="desconocido", dkim="desconocido", dmarc="desconocido"
        ),
        description="Autenticación",
    )
    urls: list[UrlResponse] = Field(
        default_factory=list, description="URLs"
    )
    adjuntos: list[AdjuntoResponse] = Field(
        default_factory=list, description="Adjuntos"
    )
    version_pesos: str = Field(default="v1", description="Versión pesos")
    version_modelo: str = Field(
        default="indeterminada", description="Versión modelo"
    )
    ticket: TicketResponse | None = Field(
        default=None, description="Ticket Jira"
    )


class AccionResponse(BaseModel):
    """Acción ejecutada o simulada."""

    ejecutada: str | None = Field(
        default=None, description="Acción ejecutada"
    )
    simulada: bool = Field(
        default=True, description="True si dry_run"
    )


class AnalisisResponse(BaseModel):
    """Respuesta estándar de análisis (§14.2)."""

    id: str = Field(description="ID del análisis")
    origen: OrigenAPI = Field(description="Origen")
    modo: ModoAPI = Field(description="Modo de creación")
    creado_en: datetime = Field(description="Timestamp")
    duracion_ms: int = Field(ge=0, description="Duración en ms")
    correo: CorreoResponse = Field(description="Correo enmascarado")
    resultado: ResultadoResponse = Field(description="Resultado")
    accion: AccionResponse = Field(description="Acción")
    retroalimentacion: Feedback | None = Field(
        default=None, description="Feedback del usuario"
    )


class AnalisisPaginadoResponse(BaseModel):
    """Lista paginada de análisis."""

    items: list[AnalisisResponse] = Field(
        default_factory=list, description="Página de resultados"
    )
    pagina: int = Field(ge=1, description="Página actual")
    limite: int = Field(ge=1, description="Tamaño de página")
    total: int = Field(ge=0, description="Total de resultados")


class FeedbackRequest(BaseModel):
    """PATCH /analyses/{id}/feedback body."""

    feedback: Feedback = Field(description="Feedback del usuario")


class MuestraResponse(BaseModel):
    """Muestra para el modo muestra [PROPUESTA]."""

    id: str = Field(description="ID de la muestra")
    nombre: str = Field(description="Nombre")
    descripcion: str = Field(description="Descripción")
    contenido: str = Field(description="Texto del correo de ejemplo")
