"""Modelos de datos del cliente VirusTotal (spec 006, módulo M06).

Constantes y catálogo con valores LITERALES de M06.1–M06.4, la tabla de
variables del plan maestro y los catálogos 5.2/5.3 (Art. VI.2): nada se
inventa. `puntos`/`severidad` se COPIAN del catálogo, nunca se calculan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# --- Constantes (literales M06.1–M06.4 / tabla 14.x, Art. III.6) ---

TOPE_RPM_PUBLIC: Final[int] = 4
"""4 solicitudes por minuto en modo public (M06.1/M06.3)."""

TOPE_DIA_PUBLIC: Final[int] = 500
"""500 solicitudes por día en modo public (M06.1/M06.3)."""

REINTENTOS_MAX: Final[int] = 3
"""Hasta 3 reintentos en 429/5xx (M06.3)."""

ESPERA_BASE_SEGUNDOS: Final[float] = 1.0
"""Espera exponencial base: 1 s, 2 s, 4 s (M06.3)."""

FALLOS_CORTACIRCUITO: Final[int] = 5
"""El cortacircuitos abre tras 5 fallos consecutivos (FR-004)."""

VENTANA_CORTACIRCUITO_SEGUNDOS: Final[float] = 60.0
"""La ventana del cortacircuitos dura 60 s (FR-004)."""

TTL_ARCHIVO_DIAS: Final[int] = 7
"""TTL de caché para archivos: 7 días (FR-005)."""

TTL_URL_DIAS: Final[int] = 1
"""TTL de caché para URLs, dominios e IPs: 24 horas (FR-005)."""

TTL_DESCONOCIDO_HORAS: Final[int] = 1
"""TTL de caché para resultados desconocidos (404): 1 hora (FR-005)."""

MAX_CONSULTAS_POR_CORREO: Final[int] = 10
"""Default de VT_MAX_POR_CORREO: 10 consultas externas por correo (FR-006)."""

TIMEOUT_CONEXION_SEGUNDOS: Final[float] = 3.0
"""Timeout de conexión de 3 s (M06.3)."""

TIMEOUT_LECTURA_SEGUNDOS: Final[float] = 10.0
"""Timeout de lectura de 10 s (M06.3)."""

BASE_VT: Final[str] = "https://www.virustotal.com/api/v3"
"""Base del API v3 de VirusTotal (M06.2)."""

ESPERA_ANALISIS_URL_SEGUNDOS: Final[float] = 5.0
"""Espaciado de 5 s entre consultas de GET /analyses/{id} (M06.2)."""

TOPE_CONSULTAS_ANALISIS_URL: Final[int] = 3
"""Máximo 3 consultas de GET /analyses/{id} tras enviar una URL (M06.2)."""

UMBRAL_MALICIOSA: Final[int] = 3
"""malicious >= 3 → maliciosa (M06.4/FR-007)."""

UMBRAL_SOSPECHOSA: Final[int] = 3
"""suspicious >= 3 → sospechosa (M06.4/FR-007)."""

UMBRAL_LIMPIA: Final[int] = 20
"""harmless + undetected >= 20 → limpia (M06.4/FR-007)."""

# --- Tipos literales ---

Clasificacion = Literal["maliciosa", "sospechosa", "limpia", "desconocida"]
TipoIndicador = Literal["archivo", "url", "dominio", "ip"]
FuenteVT = Literal["red", "cache", "sin_llamada"]
SeveridadVT = Literal["media", "alta", "informativa"]

# --- Catálogo VT (transcripción literal de los catálogos 5.2/5.3) ---
# Los códigos VT_* pertenecen a la spec 006 (Art. VI.2, fuente única).
# Severidad y puntos se copian de aquí; las strategies nunca inventan pesos.

CATALOGO_VT: Final[dict[str, tuple[SeveridadVT, int]]] = {
    "VT_URL_SOSPECHOSA": ("alta", 20),
    "VT_ADJ_SOSPECHOSO": ("alta", 25),
    "VT_DESCONOCIDO": ("informativa", 0),
    "VT_NO_DISPONIBLE": ("informativa", 0),
    "VT_PRESUPUESTO_AGOTADO": ("informativa", 0),
}

ORDEN_CATALOGO_VT: Final[tuple[str, ...]] = tuple(CATALOGO_VT)


# --- Entrada del clasificador ---


class LastAnalysisStats(BaseModel):
    """`data.attributes.last_analysis_stats` de VirusTotal (M06.4).

    Solo participan los 4 campos de la tabla de decisión; los demás
    (`timeout`, `failure`) se descartan al parsear. Campos faltantes → 0.
    """

    malicious: int = Field(default=0, ge=0)
    suspicious: int = Field(default=0, ge=0)
    harmless: int = Field(default=0, ge=0)
    undetected: int = Field(default=0, ge=0)


# --- Salida pública ---


class BanderaVT(BaseModel):
    """Flag del catálogo VT, con shape compatible con 003/004/005.

    `severidad`/`puntos` se copian de `CATALOGO_VT` (Art. VI.2); `detalle`
    cita tipo + identificador saneado, jamás la URL original con parámetros,
    la clave ni PII (Art. V.4, AC-VT-07).
    """

    codigo: str
    severidad: SeveridadVT
    puntos: int = Field(ge=0)
    detalle: str = Field(min_length=1)

    @field_validator("codigo")
    @classmethod
    def _codigo_en_catalogo(cls, valor: str) -> str:
        """Rechaza códigos fuera del catálogo VT (fuente única, Art. VI.2)."""
        if valor not in CATALOGO_VT:
            raise ValueError(f"código VT fuera del catálogo: {valor!r}")
        return valor


def bandera(codigo: str, detalle: str) -> BanderaVT:
    """Crea una bandera COPIANDO severidad/puntos del catálogo (Art. VI.2)."""
    severidad, puntos = CATALOGO_VT[codigo]
    return BanderaVT(codigo=codigo, severidad=severidad, puntos=puntos, detalle=detalle)


class ResultadoVT(BaseModel):
    """Resultado de una consulta VT (salida pública del cliente).

    Invariantes (data-model.md IV1–IV4): `limpia` solo con datos reales;
    `sin_llamada` ⇒ `desconocida`; ninguna entrada del consumidor lanza
    excepción (III.9); misma entrada + mismas respuestas ⇒ mismo resultado.
    """

    tipo: TipoIndicador
    identificador: str = Field(min_length=1)
    clasificacion: Clasificacion
    fuente: FuenteVT
    banderas: list[BanderaVT] = Field(default_factory=list)
    stats: LastAnalysisStats | None = None
    consultas_externas: int = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _invariantes(self) -> ResultadoVT:
        """Valida IV1–IV4 y la coherencia de banderas/consultas (interno)."""
        if self.fuente == "sin_llamada" and self.clasificacion != "desconocida":
            raise ValueError("IV2: fuente='sin_llamada' exige clasificacion='desconocida'")
        if self.clasificacion == "limpia" and (self.fuente == "sin_llamada" or self.stats is None):
            raise ValueError("IV1: 'limpia' exige fuente real y stats completos")
        if self.fuente == "red" and self.consultas_externas != 1:
            raise ValueError("fuente='red' exige consultas_externas=1")
        if self.fuente != "red" and self.consultas_externas != 0:
            raise ValueError("fuente no-red exige consultas_externas=0")
        codigos = [b.codigo for b in self.banderas]
        if len(codigos) != len(set(codigos)):
            raise ValueError("códigos de bandera duplicados")
        if codigos != sorted(codigos, key=ORDEN_CATALOGO_VT.index):
            raise ValueError("banderas fuera del orden de CATALOGO_VT")
        return self


@dataclass(frozen=True)
class EntradaCache:
    """Entrada de `vt_cache` inmutable (FR-005, data-model.md).

    `clave` tiene el formato `"{tipo}:{identificador}"`; `expira_en` es lo
    que indexa MongoDB con el índice TTL (`expireAfterSeconds=0`).
    """

    clave: str
    clasificacion: Clasificacion
    stats: LastAnalysisStats | None
    guardada_en: datetime
    expira_en: datetime
