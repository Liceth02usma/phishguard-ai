"""Modelos del análisis de URLs (spec 004): catálogo 5.2 y tipos de salida.

Art. VI.2: los códigos, severidades y puntos son transcripción literal del
catálogo 5.2 de `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`; las estrategias
nunca inventan pesos — usan `bandera()`, que los copia del catálogo (I5).
Los códigos `VT_*` pertenecen a la spec 006 y NO viven aquí (VI.1).
"""

from __future__ import annotations

import ipaddress
import re
from typing import Final, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CodigoBandaURL = Literal[
    "URL_TEXTO_DISTINTO_DESTINO",
    "URL_HOST_IP",
    "URL_ACORTADA",
    "URL_ARROBA",
    "URL_PUNYCODE",
    "URL_TLD_RIESGO",
    "URL_SUBDOMINIOS_EXCESIVOS",
    "URL_PUERTO_NO_ESTANDAR",
    "URL_HTTP_SIN_CIFRADO",
    "URL_LARGA",
    "URL_PARAMETROS_SENSIBLES",
    "REDIRECCION_EXCESIVA",
    "URL_DOMINIO_NUEVO",
]

SeveridadURL = Literal["baja", "media", "alta"]

EstadoExpansion = Literal[
    "no_acortadora",
    "reputacion_conocida",
    "expandida",
    "limite_saltos",
    "limite_tiempo",
    "bloqueada_ssrf",
    "esquema_no_permitido",
    "error_controlado",
]

# Catálogo 5.2 — los 13 códigos de URL (transcripción literal, fuente única).
CATALOGO_URL: Final[dict[CodigoBandaURL, tuple[SeveridadURL, int]]] = {
    "URL_TEXTO_DISTINTO_DESTINO": ("alta", 20),
    "URL_HOST_IP": ("alta", 15),
    "URL_ACORTADA": ("media", 10),
    "URL_ARROBA": ("media", 10),
    "URL_PUNYCODE": ("media", 10),
    "URL_TLD_RIESGO": ("baja", 5),
    "URL_SUBDOMINIOS_EXCESIVOS": ("baja", 5),
    "URL_PUERTO_NO_ESTANDAR": ("baja", 5),
    "URL_HTTP_SIN_CIFRADO": ("baja", 5),
    "URL_LARGA": ("baja", 3),
    "URL_PARAMETROS_SENSIBLES": ("media", 8),
    "REDIRECCION_EXCESIVA": ("media", 10),
    "URL_DOMINIO_NUEVO": ("alta", 15),
}

# Límites numéricos textuales de FR-003/FR-004/M04b (Art. VI.2: no inventados).
TOPE_SALTOS: Final[int] = 5
TIMEOUT_URL_SEGUNDOS: Final[float] = 5.0
UMBRAL_URL_LARGA: Final[int] = 200
DIAS_DOMINIO_NUEVO: Final[int] = 30

# FR-004 literal: privadas, loopback, enlace local y metadatos de nube.
# Se suma la comprobación `is_global` en ssrf.py como defensa en profundidad (D7).
REDES_PROHIBIDAS: Final[tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]] = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)

# Detalle sin direcciones de correo completas (Art. V.4 — research D12).
_CORREO_PATRON = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class BanderaURL(BaseModel):
    """Banderas activada de URL: mismos campos que la `BanderaActivada` de la 003 (D3)."""

    codigo: CodigoBandaURL = Field(description="Código del catálogo 5.2")
    severidad: SeveridadURL = Field(description="Severidad copiada del catálogo 5.2")
    puntos: int = Field(ge=0, description="Puntos copiados del catálogo 5.2")
    detalle: str = Field(min_length=1, description="Evidencia sin valores sensibles (V.4)")

    @field_validator("detalle")
    @classmethod
    def _sin_correos_completos(cls, valor: str) -> str:
        """Los detalles citan host y nombres de parámetros, nunca correos (V.4)."""
        if _CORREO_PATRON.search(valor):
            raise ValueError("el detalle no puede contener direcciones de correo")
        return valor


def bandera(codigo: CodigoBandaURL, detalle: str) -> BanderaURL:
    """Crea una bandera copiando severidad y puntos del catálogo 5.2 (I5)."""
    severidad, puntos = CATALOGO_URL[codigo]
    return BanderaURL(codigo=codigo, severidad=severidad, puntos=puntos, detalle=detalle)


class ResultadoExpansion(BaseModel):
    """Resultado de intentar expandir una URL (máquina de estados en data-model.md)."""

    estado: EstadoExpansion = Field(description="Estado final de la expansión")
    destino_final: str | None = Field(default=None, description="URL saneada final, si expandida")
    saltos: int = Field(default=0, ge=0, le=TOPE_SALTOS, description="Peticiones realizadas")
    duracion_ms: int = Field(default=0, ge=0, description="Duración medida con el reloj inyectado")
    motivo: str | None = Field(default=None, description="Causa sin PII para estados de fallo")


class UrlAnalizada(BaseModel):
    """Una URL del correo tras extracción, normalización, saneado y evaluación."""

    original: str = Field(description="URL tal cual aparece (FR-001 la conserva)")
    normalizada: str = Field(description="Host en minúsculas, sin fragmento ni tracking (FR-001)")
    host: str = Field(default="", description="Host parseado (vacío si no parseable)")
    esquema: str = Field(default="", description="Esquema detectado (http/https/otro)")
    texto_mostrado: str = Field(default="", description="Texto del enlace, si vino de uno")
    es_acortadora: bool = Field(default=False, description="Host en la lista configurable (FR-003)")
    url_saneada: str = Field(
        default="", description="Única forma que cruza a consulta externa (FR-007)"
    )
    expansion: ResultadoExpansion | None = Field(
        default=None, description="Resultado, si se evaluó"
    )
    codigos: list[CodigoBandaURL] = Field(default_factory=list, description="Códigos activados")


class EstadisticasURLs(BaseModel):
    """Contadores del resultado; invariante verificable en pruebas (I-spec)."""

    total: int = Field(ge=0)
    expandidas: int = Field(ge=0)
    bloqueadas_ssrf: int = Field(ge=0)
    sin_expansion: int = Field(ge=0)

    @model_validator(mode="after")
    def _coherentes(self) -> EstadisticasURLs:
        """Cada URL evaluada cuenta exactamente una vez en un contador."""
        if self.expandidas + self.bloqueadas_ssrf + self.sin_expansion != self.total:
            raise ValueError("estadísticas incoherentes: los contadores no suman el total")
        return self


class ResultadoURLs(BaseModel):
    """Salida pública de `analizar_urls` (contrato: contracts/analizar-urls.md §3)."""

    urls: list[UrlAnalizada] = Field(default_factory=list, description="Deduplicadas, en orden")
    banderas: list[BanderaURL] = Field(default_factory=list, description="Agregadas, orden estable")
    estadisticas: EstadisticasURLs = Field(description="Contadores de expansión")
