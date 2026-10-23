"""Modelos, catalogo, constantes y helpers de las banderas de cabeceras (spec 003).

El catalogo 5.1 es la UNICA fuente de verdad de severidad y puntos (Art. VI.2:
el codigo no admite pesos propios). Incluye el Protocol de las estrategias
(Strategy, research D2), el contexto de evaluacion y helpers puros de cabeceras
y dominios compartidos por todas las familias.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator
from src.level2_agent.models import EmailData

from .configuracion import ConfigBanderas

SEVERIDAD = Literal["baja", "media", "alta", "informativa"]

EstadoAuth = Literal[
    "desconocido",
    "pass",
    "fail",
    "softfail",
    "neutral",
    "none",
    "permerror",
    "temperror",
]

# --- Catalogo 5.1: fuente unica de verdad (codigo -> (severidad, puntos)) ---

CATALOGO_BANDERAS: dict[str, tuple[SEVERIDAD, int]] = {
    "SPF_FALLA": ("media", 10),
    "DKIM_FALLA": ("media", 10),
    "DMARC_FALLA": ("alta", 15),
    "AUTH_NO_EVALUABLE": ("baja", 5),
    "REPLY_TO_DISTINTO": ("media", 10),
    "RETURN_PATH_DISTINTO": ("baja", 5),
    "NOMBRE_SUPLANTA": ("alta", 15),
    "DOMINIO_PARECIDO": ("alta", 20),
    "DOMINIO_PUNYCODE": ("media", 10),
    "MESSAGE_ID_DISTINTO": ("baja", 5),
    "RECEIVED_INCONSISTENTE": ("media", 10),
    "FECHA_ANOMALA": ("baja", 5),
    "REPLY_TO_GRATUITO": ("media", 10),
    "REMITENTE_EXTERNO_COMO_INTERNO": ("alta", 15),
    "DOMINIO_NUEVO": ("alta", 15),
    "DOMINIO_EDAD_DESCONOCIDA": ("informativa", 0),
}

# --- Constantes de umbral (Art. III.6: sin numeros magicos) ---

TOPE_PUNTOS_BANDERAS = 60
"""Tope total de puntos de todas las banderas del correo (catalogo 5.1, AC-HDR-05)."""

UMBRAL_DISTANCIA_EDICION = 2
"""Distancia de edicion maxima para considerar un dominio parecido (M03)."""

DIAS_CACHE_RDAP = 7
"""TTL de la cache de exitos RDAP en dias (FR-006)."""

TIMEOUT_RDAP_SEGUNDOS = 5
"""Tiempo maximo de espera de una consulta RDAP (FR-006)."""

DIAS_DOMINIO_NUEVO = 30
"""Un dominio registrado hace menos de estos dias es DOMINIO_NUEVO (catalogo 5.1)."""

DIAS_FECHA_FUTURA = 1
"""Mas de estos dias en el futuro es FECHA_ANOMALA (catalogo 5.1: 24 h)."""

ANIOS_FECHA_VIEJA = 1
"""Mas de estos anios en el pasado es FECHA_ANOMALA (catalogo 5.1)."""

MAPA_HOMOGLIFOS: dict[str, str] = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "і": "i", "ѕ": "s", "ј": "j", "һ": "h", "ԁ": "d", "ԛ": "q",
    "ԝ": "w", "у": "y", "Α": "A", "Ε": "E", "Ο": "O", "Ρ": "P",
    "Τ": "T", "Χ": "X", "α": "a", "ε": "e", "ο": "o", "ρ": "p",
    "τ": "t", "χ": "x", "ν": "v", "μ": "u",
}
"""Pares homoglifo→latino para normalizar antes de comparar (research D6)."""

REDES_PRIVADAS: tuple[str, ...] = (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8",
    "169.254.0.0/16", "100.64.0.0/10", "::1/128", "fc00::/7", "fe80::/10",
)
"""Redes privadas/reservadas que no deben aparecer en el primer salto externo (M04b)."""

_RE_DIRECCION = re.compile(r"<([^>]+)>")


def severidad_de(codigo: str) -> SEVERIDAD:
    """Devuelve la severidad catalogada de ``codigo``."""
    return CATALOGO_BANDERAS[codigo][0]


def puntos_de(codigo: str) -> int:
    """Devuelve los puntos catalogados de ``codigo``."""
    return CATALOGO_BANDERAS[codigo][1]


def orden_de_catalogo(codigo: str) -> int:
    """Indice de orden del ``codigo`` en el catalogo (para salida estable)."""
    return list(CATALOGO_BANDERAS).index(codigo)


# --- Helpers puros de cabeceras y dominios ---


def obtener_cabeceras(correo: EmailData, nombre: str) -> list[str]:
    """Valores de la cabecera ``nombre`` (insensible a mayusculas, en orden fisico)."""
    n = nombre.lower()
    return [c.valor for c in correo.cabeceras if c.nombre.lower() == n]


def primer_valor(correo: EmailData, nombre: str) -> str | None:
    """Primera aparicion de la cabecera ``nombre`` o ``None`` si no existe."""
    vals = obtener_cabeceras(correo, nombre)
    return vals[0] if vals else None


def _direccion(valor: str) -> str:
    """Extrae la direccion dentro de ``<...>`` o devuelve el valor tal cual."""
    m = _RE_DIRECCION.search(valor)
    return m.group(1).strip() if m else valor.strip()


def dominio_de(valor: str) -> str | None:
    """Dominio (en minusculas, sin punto final) de un valor tipo correo, o ``None``."""
    dir_ = _direccion(valor)
    if "@" not in dir_:
        return None
    dom = dir_.rsplit("@", 1)[1].strip().lower().rstrip(".")
    return dom or None


def nombre_visible(valor: str) -> str:
    """Nombre visible (antes de ``<``) de un valor ``From``; vacio si no hay."""
    v = valor.strip()
    if "<" not in v:
        return ""
    return v.split("<", 1)[0].strip().strip("\"'").strip()


def fabricar_bandera(codigo: str, detalle: str) -> BanderaActivada:
    """Crea una ``BanderaActivada`` tomando severidad y puntos del catalogo.

    Las estrategias solo aportan ``codigo`` y ``detalle``; los pesos vienen del
    catalogo para que jamás se inventen (Art. VI.2).
    """
    return BanderaActivada(
        codigo=codigo,
        severidad=severidad_de(codigo),
        puntos=puntos_de(codigo),
        detalle=detalle,
    )


class BanderaActivada(BaseModel):
    """Una bandera del catalogo 5.1 activada para el correo."""

    codigo: str = Field(description="Codigo del catalogo 5.1")
    severidad: SEVERIDAD = Field(description="Severidad catalogada")
    puntos: int = Field(ge=0, description="Puntos catalogados")
    detalle: str = Field(min_length=1, description="Evidencia en dominios, sin PII")

    @field_validator("codigo")
    @classmethod
    def _codigo_en_catalogo(cls, v: str) -> str:
        if v not in CATALOGO_BANDERAS:
            raise ValueError(f"codigo fuera del catalogo 5.1: {v}")
        return v


class EstadosAutenticacion(BaseModel):
    """Estados SPF/DKIM/DMARC derivados del Authentication-Results (FR-002)."""

    spf: EstadoAuth = Field(default="desconocido", description="Estado de SPF")
    dkim: EstadoAuth = Field(default="desconocido", description="Estado de DKIM")
    dmarc: EstadoAuth = Field(default="desconocido", description="Estado de DMARC")


@dataclass(frozen=True)
class ResultadoAutenticacion:
    """Estados y si existio un Authentication-Results de confianza (FR-001/FR-002)."""

    estados: EstadosAutenticacion
    hay_confiable: bool


class ResultadoBanderas(BaseModel):
    """Salida de ``evaluar_banderas``: banderas + autenticacion + puntos."""

    banderas: list[BanderaActivada] = Field(default_factory=list)
    estados_autenticacion: EstadosAutenticacion = Field(default_factory=EstadosAutenticacion)
    puntos_totales: int = Field(ge=0, description="Suma de puntos con tope de 60")

    @field_validator("puntos_totales")
    @classmethod
    def _puntos_con_tope(cls, v: int) -> int:
        if v > TOPE_PUNTOS_BANDERAS:
            raise ValueError(f"puntos_totales supera el tope {TOPE_PUNTOS_BANDERAS}")
        return v

    @model_validator(mode="after")
    def _sin_codigos_repetidos(self) -> ResultadoBanderas:
        codigos = [b.codigo for b in self.banderas]
        if len(codigos) != len(set(codigos)):
            raise ValueError("banderas con codigos repetidos")
        return self


class EvaluadorBandera(Protocol):
    """Interfaz Strategy de una bandera (research D2)."""

    codigo: str

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        """Devuelve la bandera activada o ``None`` si no aplica."""
        ...


@dataclass(frozen=True)
class ContextoEvaluacion:
    """Lo que toda estrategia necesita: correo, config, reloj, auth y puente RDAP."""

    correo: EmailData
    config: ConfigBanderas
    ahora: datetime
    autenticacion: ResultadoAutenticacion
    consultar_fecha_registro: Callable[[str], datetime | None]


def valores_de(campo: Sequence[str] | None) -> list[str]:
    """Normaliza una secuencia opcional a lista (helper para estrategias)."""
    return list(campo) if campo else []
