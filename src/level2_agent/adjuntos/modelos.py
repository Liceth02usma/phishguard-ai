"""Modelos de datos del análisis de adjuntos (spec 005, módulo M05).

Catálogo 5.3 como fuente única de verdad (Art. VI.2), constantes de límite
(Art. III.6), protocolo de detectores y modelos Pydantic públicos (Art. III.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from src.level2_agent.adjuntos.configuracion import ConfigAdjuntos

Severidad = Literal["media", "alta"]
"""Severidades del catálogo 5.3 para banderas de adjuntos (sin `informativa`)."""

# --- Catálogo 5.3 (transcripción literal de docs/PLAN_MODIFICACIONES 5.3) ---
# Art. VI.2: el código no admite puntos propios. VT_ADJ_SOSPECHOSO (alta/25)
# pertenece a la spec 006 (veredicto de VirusTotal) y NO se emite aquí.
CATALOGO_ADJUNTOS: dict[str, tuple[Severidad, int]] = {
    "ADJ_EXTENSION_RIESGO": ("alta", 20),
    "ADJ_DOBLE_EXTENSION": ("alta", 20),
    "ADJ_TIPO_NO_COINCIDE": ("alta", 15),
    "ADJ_MACRO": ("alta", 20),
    "ADJ_ENLACE_EXTERNO": ("media", 10),
    "ADJ_PDF_ACTIVO": ("media", 10),
    "ADJ_CIFRADO": ("media", 12),
    "ADJ_ARCHIVO_SOSPECHOSO": ("alta", 15),
    "ADJ_HTML": ("media", 10),
}

# --- Constantes de límite (FR-005, Art. III.6) ---
ADJ_LIMITE_ENTRADAS_ZIP = 100
"""Máximo de entradas en un zip (FR-005)."""

ADJ_LIMITE_DESCOMPRIMIDO_ZIP = 100 * 1024 * 1024
"""Máximo de bytes descomprimidos en un zip: 100 MiB (FR-005; MB = MiB, spec 002)."""

ADJ_RATIO_MAXIMO_ZIP = 100
"""Relación máxima de compresión permitida (FR-005); >100:1 aborta."""

# --- Defaults de listas configurables (M05, research D4) ---
EXTENSIONES_RIESGO_DEFAULT: frozenset[str] = frozenset(
    {"exe", "scr", "com", "msi", "dll", "js", "vbs", "ps1", "bat", "cmd",
     "hta", "wsf", "lnk", "iso", "img", "vhd"}
)
EXTENSIONES_HTML_DEFAULT: frozenset[str] = frozenset({"html", "htm", "svg"})
EXTENSIONES_DOCUMENTAL_DEFAULT: frozenset[str] = frozenset(
    {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
     "odt", "ods", "odp", "txt", "csv", "jpg", "jpeg", "png", "gif"}
)


# --- Modelos Pydantic públicos (Art. III.4) ---


class BanderaAdjunto(BaseModel):
    """Bandera activada para un adjunto (código, severidad, puntos, detalle)."""

    codigo: str
    severidad: Severidad
    puntos: int = Field(ge=0)
    detalle: str = Field(min_length=1)

    @field_validator("codigo")
    @classmethod
    def _validar_codigo(cls, v: str) -> str:
        """Valida que el código pertenezca al catálogo 5.3."""
        if v not in CATALOGO_ADJUNTOS:
            raise ValueError(f"código de bandera desconocido: {v}")  # noqa: TRY003
        return v


class AnalisisAdjunto(BaseModel):
    """Resultado del análisis estático de un adjunto (salida de analizar_adjunto)."""

    nombre: str
    tipo_declarado: str = ""
    tipo_real: str = "desconocido"
    tamano_bytes: int = Field(default=0, ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    md5: str = Field(pattern=r"^[0-9a-f]{32}$")
    sha1: str = Field(pattern=r"^[0-9a-f]{40}$")
    banderas: list[BanderaAdjunto] = Field(default_factory=list)
    detalles: list[str] = Field(default_factory=list)


def bandera(codigo: str, detalle: str) -> BanderaAdjunto:
    """Construye una BanderaAdjunto copiando severidad/puntos del catálogo (Art. VI.2).

    Los detectores solo aportan código + detalle; el catálogo es la fuente de
    severidad y puntos (nunca se inventan).
    """
    severidad, puntos = CATALOGO_ADJUNTOS[codigo]
    return BanderaAdjunto(codigo=codigo, severidad=severidad, puntos=puntos, detalle=detalle)


# --- Objetos internos (dataclass frozen, no contrato público) ---


@dataclass(frozen=True)
class ContextoAdjunto:
    """Contexto compartido por todos los detectores para un adjunto.

    El motor lo construye una vez a partir de (nombre, tipo_declarado, payload, config).
    """

    nombre: str
    extension_final: str
    extensiones_previas: tuple[str, ...]
    tipo_real: str
    tipo_declarado: str
    payload: bytes
    config: ConfigAdjuntos


@dataclass(frozen=True)
class ResultadoDetector:
    """Salida de un detector: banderas activadas + detalles de degradación."""

    banderas: tuple[BanderaAdjunto, ...]
    detalles: tuple[str, ...]


class Detector(Protocol):
    """Interfaz común de los detectores (Strategy, research D2)."""

    def evaluar(self, ctx: ContextoAdjunto) -> ResultadoDetector:
        """Evalúa el adjunto y devuelve banderas + detalles (nunca lanza)."""
        ...
