"""Modelos de datos del agente de IA sin estado (spec 009, M07).

EntradaAgente agrupa toda la evidencia calculada por specs 003–007.
SalidaAgente es el esquema validado de la salida del modelo.
ResultadoAgente es la salida del orquestador (para el motor de decisión).
ModeloLLM es el Protocol para el adapter del modelo (FR-008).

Constantes y límites son LITERALES de M07 (Art. VI.2).
"""

from __future__ import annotations

from typing import Final, Literal, Protocol

from pydantic import BaseModel, Field, field_validator

from src.level2_agent.adjuntos.modelos import AnalisisAdjunto
from src.level2_agent.banderas.modelos import (
    BanderaActivada,
    EstadosAutenticacion,
)
from src.level2_agent.models import EmailData
from src.level2_agent.virustotal.modelos import ResultadoVT
from src.level3_logic.scoring.modelos import ScoreFinal

# --- Constantes de configuración (Art. III.6: sin números mágicos) ---

LLM_MAX_DIARIO_DEFAULT: Final[int] = 100
"""Tope diario por defecto (M07, FR-007)."""

LLM_MODELO_DEFAULT: Final[str] = "models/gemini-2.5-flash-lite"
"""Modelo por defecto (M07, FR-008)."""

LLM_TEMPERATURA: Final[float] = 0.0
"""Temperatura 0 para determinismo máximo (M07)."""

MAX_REINTENTOS: Final[int] = 1
"""1 reintento si la salida no valida (M07, AC-AGT-03)."""

# --- Delimitadores de seguridad (M07, FR-003) ---

DELIM_CORREO_INICIO: Final[str] = "<correo>"
"""Delimitador de apertura del texto del correo."""

DELIM_CORREO_FIN: Final[str] = "</correo>"
"""Delimitador de cierre del texto del correo."""

# --- Límites de longitud del esquema de salida (M07) ---

LIMITE_RESUMEN: Final[int] = 500
LIMITE_ANALISIS: Final[int] = 2000
LIMITE_INDICADORES_CANTIDAD: Final[int] = 10
LIMITE_INDICADOR_CHARS: Final[int] = 200
LIMITE_JUSTIFICACION: Final[int] = 1000

NivelSeveridadAgente = Literal["Bajo", "Medio", "Alto", "Crítico"]
"""Nivel de severidad en la salida del agente (M07)."""


# --- Modelos Pydantic (Art. III.4) ---


class EntradaAgente(BaseModel):
    """Entrada del agente: toda la evidencia calculada por specs 003–007.

    El orquestador del pipeline construye este objeto tras ejecutar
    las specs 003–007. El agente no llama servicios externos (excepto
    RAG de solo lectura).
    """

    email_data: EmailData = Field(description="Correo normalizado (spec 002)")
    score_final: ScoreFinal = Field(description="Score compuesto (spec 007)")
    banderas_cabeceras: list[BanderaActivada] = Field(
        default_factory=list, description="Banderas de cabeceras (spec 003)"
    )
    estados_autenticacion: EstadosAutenticacion = Field(
        default_factory=EstadosAutenticacion,
        description="Estados SPF/DKIM/DMARC (spec 003)",
    )
    resultado_adjuntos: list[AnalisisAdjunto] = Field(
        default_factory=list, description="Análisis de adjuntos (spec 005)"
    )
    resultados_vt: list[ResultadoVT] = Field(
        default_factory=list, description="Veredictos VirusTotal (spec 006)"
    )


class SalidaAgente(BaseModel):
    """Salida validada del modelo (esquema M07, FR-004).

    Longitudes máximas para limitar la salida y facilitar validación.
    """

    resumen: str = Field(
        max_length=LIMITE_RESUMEN,
        description="Resumen ejecutivo del análisis",
    )
    analisis_tecnico: str = Field(
        max_length=LIMITE_ANALISIS,
        description="Evaluación técnica forense",
    )
    es_phishing: bool = Field(description="Opinión del agente sobre phishing")
    indicadores_phishing: list[str] = Field(
        max_length=LIMITE_INDICADORES_CANTIDAD,
        description="Patrones de riesgo (max 10)",
    )
    nivel_severidad: NivelSeveridadAgente = Field(
        description="Severidad opinada: Bajo/Medio/Alto/Crítico"
    )
    justificacion_veredicto: str = Field(
        max_length=LIMITE_JUSTIFICACION,
        description="Justificación citando NIST/OWASP",
    )

    @field_validator("indicadores_phishing")
    @classmethod
    def _limitar_indicadores_chars(cls, v: list[str]) -> list[str]:
        """Cada indicador no debe exceder LIMITE_INDICADOR_CHARS."""
        for i, ind in enumerate(v):
            if len(ind) > LIMITE_INDICADOR_CHARS:
                raise ValueError(
                    f"indicadores_phishing[{i}] excede {LIMITE_INDICADOR_CHARS} chars"
                )
        return v


class ResultadoAgente(BaseModel):
    """Salida del orquestador del agente (para el motor de decisión, spec 008).

    Si salida es None, el agente no pudo producir un resultado válido
    (tope superado o validación fallida). confirmacion_agente es None
    en ese caso, y el motor de decisión trata la zona gris como sospechoso.
    """

    salida: SalidaAgente | None = Field(
        default=None,
        description="Salida validada del modelo (None si falló)",
    )
    confirmacion_agente: bool | None = Field(
        default=None,
        description="True=phishing, False=no phishing, None=no consultado",
    )
    reintentos: int = Field(
        default=0, ge=0, le=2,
        description="0=éxito primer intento, 1=éxito reintento, 2=falló",
    )
    llamadas_modelo: int = Field(
        default=0, ge=0, le=2,
        description="0, 1 o 2 llamadas al modelo",
    )
    razon: Literal["exito", "tope_superado", "validacion_fallida"] = Field(
        default="exito",
        description="Razón del resultado",
    )


# --- Protocol del modelo (Adapter, FR-008) ---


class ModeloLLM(Protocol):
    """Protocol para el adapter del modelo LLM (FR-008).

    Permite tests con modelo simulado (AC-AGT-06) y cambio de modelo
    por configuración (LLM_MODELO env var).
    """

    def invocar(self, prompt: str, *, herramientas: list[object] | None = None) -> str:
        """Invoca el modelo con el prompt y retorna la respuesta cruda.

        herramientas es la lista de herramientas LangChain para el ReAct.
        """
        ...
