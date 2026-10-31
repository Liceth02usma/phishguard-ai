"""Extracción de adjuntos desde archivos EML (spec 012, AC-API-02).

Usa :mod:`email` de lastdlib para parsear MIME y extraer adjuntos
como bytes en memoria (nunca escribe a disco, Art. V.5).
"""

from __future__ import annotations

import email
from email.message import Message
from dataclasses import dataclass

MAX_ADJUNTOS_EML = 10
"""Máximo de adjuntos a extraer de un EML (Art. III.6, sin números mágicos)."""


@dataclass(frozen=True)
class AdjuntoEml:
    """Adjunto extraído de un EML (nombre, tipo declarado, payload)."""

    nombre: str
    tipo_declarado: str
    payload: bytes


def extraer_adjuntos_eml(contenido: bytes) -> list[AdjuntoEml]:
    """Extrae adjuntos de un EML parseado como MIME.

    Solo considera partes con ``Content-Disposition: attachment`` o
    partes no‑text que no sean el cuerpo principal.
    Devuelve máximo :data:`MAX_ADJUNTOS_EML` adjuntos.
    """
    msg = email.message_from_bytes(contenido)
    resultado: list[AdjuntoEml] = []

    for parte in _walk_parts(msg):
        if len(resultado) >= MAX_ADJUNTOS_EML:
            break
        adj = _parte_a_adjunto(parte)
        if adj is not None:
            resultado.append(adj)

    return resultado


def _walk_parts(msg: Message) -> list[Message]:
    """Aplana las partes MIME del mensaje."""
    partes: list[Message] = []
    if msg.is_multipart():
        for sub in msg.walk():
            if not sub.is_multipart():
                partes.append(sub)
    else:
        partes.append(msg)
    return partes


def _parte_a_adjunto(parte: Message) -> AdjuntoEml | None:
    """Convierte una parte MIME a AdjuntoEml si es un adjunto válido."""
    disposition = parte.get("Content-Disposition", "")
    content_type = parte.get_content_type() or "application/octet-stream"

    # Solo partes con attachment o non-text inline
    if "attachment" not in disposition:
        # Ignorar text/plain y text/html (cuerpo del correo)
        if content_type.startswith("text/"):
            return None

    payload = parte.get_payload(decode=True)
    if payload is None or len(payload) == 0:
        return None

    nombre = parte.get_filename() or "(sin_nombre)"
    return AdjuntoEml(nombre=nombre, tipo_declarado=content_type, payload=payload)
