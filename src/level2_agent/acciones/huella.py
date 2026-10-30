"""Huella de campaña para deduplicación de tickets Jira (spec 010, M08, FR-004).

huella = SHA-256(remitente + asunto_normalizado + dominios_ordenados)[:16]
"""

from __future__ import annotations

import hashlib
import re

from src.level2_agent.acciones.modelos import HUELLA_LONGITUD


def normalizar_asunto(asunto: str) -> str:
    """Normaliza el asunto para la huella de campaña.

    - Strip RE:/FWD:/FW: prefixes
    - Lowercase
    - Collapse whitespace
    """
    s = asunto.strip().lower()
    # Quitar prefijos RE:, FWD:, FW: (repetidos)
    s = re.sub(r"^(re|fwd|fw)\s*:\s*", "", s, flags=re.IGNORECASE).strip()
    # Colapsar whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def extraer_dominios(urls: list[str]) -> list[str]:
    """Extrae dominios registrables de las URLs, ordenados y deduplicados.

    Usa tldextract si está disponible, sino urlparse como fallback.
    """
    dominios: set[str] = set()
    for url in urls:
        try:
            import tldextract

            ext = tldextract.extract(url)
            dom = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
            if dom:
                dominios.add(dom.lower())
        except ImportError:
            # Fallback: extraer hostname
            from urllib.parse import urlparse

            parsed = urlparse(url)
            host = parsed.hostname or ""
            if host:
                dominios.add(host.lower())
    return sorted(dominios)


def calcular_huella(remitente: str, asunto: str, urls: list[str]) -> str:
    """Calcula huella SHA-256 truncada para deduplicación de tickets (FR-004).

    huella = SHA-256(remitente + asunto_normalizado + dominios_ordenados)[:16]
    """
    asunto_norm = normalizar_asunto(asunto)
    dominios = extraer_dominios(urls)
    dominios_str = ",".join(dominios)

    raw = f"{remitente}|{asunto_norm}|{dominios_str}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:HUELLA_LONGITUD]
