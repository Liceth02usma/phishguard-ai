"""Normalización y deduplicación de URLs (FR-001, research D2).

Host en minúsculas, sin fragmento y sin parámetros de seguimiento; se
deduplica TRAS normalizar conservando la URL original y el orden (AC-URL-05).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.extraccion import Candidata


def host_de(url: str) -> str:
    """Host en minúsculas; vacío si la URL no es parseable."""
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return ""
    return (host or "").lower()


def esquema_de(url: str) -> str:
    """Esquema en minúsculas; vacío si la URL no es parseable."""
    try:
        return urlsplit(url).scheme.lower()
    except ValueError:
        return ""


def normalizar_url(url: str, config: ConfigURLs) -> str:
    """Normaliza: host en minúsculas, sin fragmento, sin tracking (FR-001).

    Devuelve cadena vacía si la URL no tiene host parseable (no candidata útil).
    """
    try:
        partes = urlsplit(url)
    except ValueError:
        return ""
    if not partes.netloc:
        return ""
    parametros = [
        (clave, valor)
        for clave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if clave.lower() not in config.parametros_tracking
    ]
    return urlunsplit(
        (partes.scheme.lower(), partes.netloc.lower(), partes.path, urlencode(parametros), "")
    )


@dataclass(frozen=True)
class UrlNormalizada:
    """Par (original, normalizada) con su texto mostrado, tras deduplicar."""

    original: str
    normalizada: str
    texto: str


def normalizar_y_deduplicar(
    candidatas: Sequence[Candidata], config: ConfigURLs
) -> list[UrlNormalizada]:
    """Normaliza y deduplica preservando el orden y la primera original (AC-URL-05)."""
    vistas: dict[str, UrlNormalizada] = {}
    for candidata in candidatas:
        normalizada = normalizar_url(candidata.url, config)
        if not normalizada or normalizada in vistas:
            continue
        vistas[normalizada] = UrlNormalizada(
            original=candidata.url, normalizada=normalizada, texto=candidata.texto
        )
    return list(vistas.values())
