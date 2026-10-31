from typing import Literal

from pydantic import BaseModel, Field


class Cabecera(BaseModel):
    """Par nombre/valor de una cabecera MIME, en orden físico del mensaje."""

    nombre: str = Field(description="Nombre original de la cabecera")
    valor: str = Field(description="Valor decodificado (RFC 2047 resuelto)")


class Adjunto(BaseModel):
    """Adjunto procesado en memoria con su hash (nunca escrito a disco, Art. V.5)."""

    nombre: str = Field(
        default="adjunto_sin_nombre", description="Nombre de archivo del adjunto"
    )
    tipo_declarado: str = Field(
        default="", description="Content-Type declarado por la parte (no se infiere el real)"
    )
    tamano_bytes: int = Field(default=0, ge=0, description="Longitud del payload decodificado")
    sha256: str = Field(
        default="", pattern=r"^[0-9a-f]{64}$", description="SHA-256 en hexadecimal"
    )


class EmailData(BaseModel):
    """Correo normalizado: campos legacy (spec 000) + campos de normalización (spec 002).

    Los campos nuevos llevan default para no romper constructores existentes
    (research D4). `htmlBody` es solo en memoria: queda fuera de `model_dump`
    y del `repr` (FR-001 — nunca persistido).
    """

    htmlBody: str = Field(
        default="",
        exclude=True,
        repr=False,
        description="Cuerpo del correo en formato HTML (solo memoria, nunca persistido)",
    )
    headers: str = Field(
        default="",
        description="Cabeceras en JSON string legado (fuente de verdad: cabeceras)",
    )
    subject: str = Field(default="", description="Asunto del correo")
    recipient: str = Field(default="", description="Dirección del destinatario (to.text)")
    textBody: str = Field(default="", description="Cuerpo del correo en texto plano (crudo)")
    message_id: str = Field(default="", description="ID único del mensaje")
    cabeceras: list[Cabecera] = Field(
        default_factory=list, description="Cabeceras ordenadas, conservando repetidas"
    )
    texto_limpio: str = Field(
        default="", description="Texto visible saneado y acotado a 20 000 caracteres"
    )
    urls: list[str] = Field(
        default_factory=list, description="URLs extraídas y deduplicadas (máx. 200)"
    )
    adjuntos: list[Adjunto] = Field(
        default_factory=list, description="Adjuntos con SHA-256 (máx. 20)"
    )
    origen: Literal["gmail", "api"] = Field(
        default="gmail", description="Origen de la entrada (gmail o api; .eml es api)"
    )
    banderas: list[str] = Field(
        default_factory=list, description="LIMITE_EXCEDIDO y/o ENTRADA_DEGRADADA"
    )
    revision_manual: bool = Field(
        default=False, description="True si hay banderas: fallar hacia revisar (Art. V.1)"
    )


class PhishingReport(BaseModel):
    resumen: str = Field(description="Resumen ejecutivo del análisis del correo")
    analisis_tecnico: str = Field(description="Evaluación técnica forense de cabeceras y contenido")
    indicadores_phishing: list[str] = Field(
        description="Lista de patrones de riesgo específicos contrastados con NIST/OWASP"
    )
    es_phishing: bool = Field(description="Veredicto final de la amenaza")
    nivel_severidad: str = Field(description="Clasificación del riesgo: Bajo, Medio, Alto, Crítico")
    justificacion_veredicto: str = Field(
        description="Justificación académica citando controles NIST o directrices OWASP"
    )
    # Veredicto del motor de decisión (spec 008/010) para el ejecutor de acciones
    veredicto: str = Field(
        default="sin_indicadores",
        description="Veredicto del motor: malicioso, sospechoso, revision_manual, sin_indicadores",
    )
    # Campos de scoring con clasificador lineal (spec 007, contrato 012)
    score_clasificador: float | None = Field(
        default=None, description="Score- Score del clasificador lineal (0-100)"
    )
    version_modelo: str | None = Field(
        default=None, description="Versión del modelo de clasificador usado"
    )


SCORE_UMBRAL_BAJO = 30
SCORE_UMBRAL_ALTO = 75
SCORE_FALLBACK = 50.0

SEVERIDAD_BAJO = "Bajo"
SEVERIDAD_MEDIO = "Medio"
SEVERIDAD_ALTO = "Alto"
SEVERIDAD_CRITICO = "Crítico"

TOP_K_RAG = 5
VECTOR_DATABASE = "phishguard"
VECTOR_COLLECTION = f"{VECTOR_DATABASE}.docs_phishing"
VECTOR_INDEX = "vector_index"
