"""Identificadores y validación de indicadores (spec 006, research D7).

SHA-256 hex-64, URL saneada → Base64 url-safe sin relleno, dominio e IP.
El saneado de URLs DELEGA en `sanitizacion.sanitizar_parametros` de la spec
004 (D7): se importa, nunca se duplica ni se modifica (Art. VI.2). Todas
las funciones son puras y jamás lanzan sobre entrada del consumidor (III.9).
"""

from __future__ import annotations

import base64
import ipaddress
import re
from urllib.parse import urlsplit

from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.sanitizacion import sanitizar_parametros

_PATRON_SHA256 = re.compile(r"\A[0-9a-fA-F]{64}\Z")
_PATRON_DOMINIO = re.compile(
    r"\A(?=.{1,253}\Z)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}\Z"
)


def normalizar_sha256(sha256: str) -> str | None:
    """Hash en minúsculas si es hex-64; None si no (G12: nunca lanza)."""
    if not _PATRON_SHA256.fullmatch(sha256):
        return None
    return sha256.lower()


def validar_url(url: str) -> str | None:
    """URL recortada con esquema http(s) y host; None si no tiene forma (G12)."""
    candidata = url.strip()
    if not candidata:
        return None
    partes = urlsplit(candidata)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return None
    return candidata


def sanitizar_url(url: str) -> str:
    """URL sin parámetros sensibles: delega en la spec 004 (D7, AC-VT-07)."""
    return sanitizar_parametros(url, ConfigURLs())


def id_url_base64(url: str) -> str:
    """Identificador Base64 url-safe SIN relleno de la URL saneada (M06.2, G7)."""
    codificado = base64.urlsafe_b64encode(sanitizar_url(url).encode("utf-8")).decode("ascii")
    return codificado.rstrip("=")


def validar_dominio(dominio: str) -> str | None:
    """Dominio en minúsculas con forma válida; None si no la tiene (G12)."""
    candidato = dominio.strip().lower().rstrip(".")
    if not _PATRON_DOMINIO.fullmatch(candidato):
        return None
    return candidato


def validar_ip(ip: str) -> str | None:
    """IP canónica (IPv4/IPv6) o None si no es válida (G12, nunca lanza)."""
    try:
        return str(ipaddress.ip_address(ip.strip()))
    except ValueError:
        return None
