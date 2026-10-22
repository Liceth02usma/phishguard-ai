"""Extracción de URLs y adjuntos desde el correo parseado (FR-001, research D7).

Funciones puras: deduplican URLs preservando el orden y calculan el SHA-256
de cada adjunto en memoria (nunca se escribe a disco, Art. V.5). Los límites
de cantidad los aplica `limites.evaluar_limites` en el orquestador.
"""

from __future__ import annotations

import hashlib
import re

from src.level2_agent.models import Adjunto

# Atributo href de un enlace HTML (comillas simples o dobles).
_HREF_PATRON = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
# URL absoluta http/https en texto libre.
_URL_PATRON = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def _es_http(url: str) -> bool:
    """True si la cadena es una URL http/https (descarta mailto:, javascript:)."""
    return url.lower().startswith(("http://", "https://"))


def _deduplicar(urls: list[str]) -> list[str]:
    """Devuelve las URLs sin duplicados, preservando el orden de aparición."""
    vistas: set[str] = set()
    unicas: list[str] = []
    for url in urls:
        if url not in vistas:
            vistas.add(url)
            unicas.append(url)
    return unicas


def extraer_urls(html: str, texto: str) -> list[str]:
    """Extrae las URLs de http/https del HTML (href y texto) y del texto plano.

    Args:
        html: cuerpo HTML original (puede ser vacío).
        texto: cuerpo de texto plano original (puede ser vacío).

    Returns:
        Lista de URLs únicas en orden de aparición (sin límite; lo aplica
        `evaluar_limites`).
    """
    candidatas: list[str] = []
    for url in _HREF_PATRON.findall(html):
        url = url.strip()
        if _es_http(url):
            candidatas.append(url)
    for url in _URL_PATRON.findall(html):
        candidatas.append(url)
    for url in _URL_PATRON.findall(texto):
        candidatas.append(url)
    return _deduplicar(candidatas)


def extraer_adjuntos(crudos: list[tuple[str, str, bytes]]) -> list[Adjunto]:
    """Convierte los adjuntos crudos en `Adjunto` con su SHA-256 calculado.

    Args:
        crudos: tuplas (nombre, tipo declarado, payload) producidas por el parseo.

    Returns:
        Lista de `Adjunto` con el hash SHA-256 en hexadecimal de cada payload.
    """
    resultado: list[Adjunto] = []
    for nombre, tipo, payload in crudos:
        resultado.append(
            Adjunto(
                nombre=nombre or "adjunto_sin_nombre",
                tipo_declarado=tipo,
                tamano_bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
            )
        )
    return resultado
