"""Modelos de error uniforme (spec 012, FR-002).

ErrorEnvelope: { error: { codigo, mensaje, detalles } }
Códigos: NO_AUTENTICADO, NO_ENCONTRADO, ENTRADA_GRANDE,
VALIDACION, DEMASIADAS_SOLICITUDES, ERROR_INTERNO,
SERVICIO_NO_DISPONIBLE.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CodigoError = Literal[
    "NO_AUTENTICADO",
    "NO_ENCONTRADO",
    "ENTRADA_GRANDE",
    "VALIDACION",
    "DEMASIADAS_SOLICITUDES",
    "ERROR_INTERNO",
    "SERVICIO_NO_DISPONIBLE",
]


class ErrorDetail(BaseModel):
    """Detalle interno del envelope de error."""

    codigo: CodigoError = Field(description="Código máquina del error")
    mensaje: str = Field(description="Mensaje humano del error")
    detalles: str | list[Any] | dict[str, Any] | None = Field(
        default=None, description="Detalle adicional"
    )


class ErrorEnvelope(BaseModel):
    """Envelope uniforme de error (FR-002)."""

    error: ErrorDetail = Field(description="Detalle del error")


# --- Excepciones custom ---


class APIError(Exception):
    """Excepción base para errores de la API."""

    def __init__(
        self,
        status_code: int,
        codigo: CodigoError,
        mensaje: str,
        detalles: str | list[Any] | dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles
        super().__init__(mensaje)


class NoAutenticadoError(APIError):
    """401: falta o inválida X-API-Key."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            codigo="NO_AUTENTICADO",
            mensaje="Falta o es inválida la cabecera X-API-Key.",
        )


class NoEncontradoError(APIError):
    """404: recurso inexistente."""

    def __init__(self, recurso: str = "Análisis") -> None:
        super().__init__(
            status_code=404,
            codigo="NO_ENCONTRADO",
            mensaje=f"{recurso} no encontrado.",
        )


class EntradaGrandeError(APIError):
    """413: entrada mayor de 25 MB."""

    def __init__(self) -> None:
        super().__init__(
            status_code=413,
            codigo="ENTRADA_GRANDE",
            mensaje="El archivo excede el límite de 25 MB.",
        )


class DemasiadasSolicitudesError(APIError):
    """429: límite de tasa excedido."""

    def __init__(self) -> None:
        super().__init__(
            status_code=429,
            codigo="DEMASIADAS_SOLICITUDES",
            mensaje="Se excedieron 30 análisis en un minuto.",
        )


class ServicioNoDisponibleError(APIError):
    """503: servicio externo no disponible (FR-002)."""

    def __init__(self, servicio: str = "servicio externo") -> None:
        super().__init__(
            status_code=503,
            codigo="SERVICIO_NO_DISPONIBLE",
            mensaje=f"{servicio} no disponible temporalmente.",
        )
