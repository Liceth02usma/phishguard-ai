"""Parseo MIME de la entrada a la estructura interna `CorreoBruto` (FR-002, research D2).

Usa la biblioteca estándar `email` con ``policy=default``: respeta el orden
físico de las cabeceras y conserva las repetidas (AC-NORM-01). Nunca lanza
excepción no controlada: las entradas degradadas se marcan y se devuelven
parciales (AC-NORM-06).
"""

from __future__ import annotations

import email
from dataclasses import dataclass, field
from email import policy
from email.message import Message

from src.level2_agent.models import Cabecera


@dataclass
class CorreoBruto:
    """Salida del parseo MIME, antes de saneado, límites y enmascarado.

    Attributes:
        cabeceras: pares nombre/valor en orden físico, con repetidas.
        cuerpo_html: cuerpo HTML original (solo en memoria).
        cuerpo_texto: cuerpo de texto plano original (solo en memoria).
        bytes_totales: longitud en bytes de la entrada cruda.
        profundidad_mime: profundidad máxima de partes MIME anidadas.
        problemas: descripciones de degradaciones detectadas (codificación, etc.).
        adjuntos_crudos: pares (nombre, tipo declarado, payload) en memoria.
    """

    cabeceras: list[Cabecera] = field(default_factory=list)
    cuerpo_html: str = ""
    cuerpo_texto: str = ""
    bytes_totales: int = 0
    profundidad_mime: int = 0
    problemas: list[str] = field(default_factory=list)
    adjuntos_crudos: list[tuple[str, str, bytes]] = field(default_factory=list)


def _extraer_cabeceras(msg: Message) -> list[Cabecera]:
    """Devuelve las cabeceras en orden físico, conservando las repetidas."""
    return [Cabecera(nombre=n, valor=v) for n, v in msg.raw_items()]


def _decodificar_parte(part: Message, problemas: list[str]) -> str:
    """Decodifica una parte de texto; ante codificación inválida degrada con `replace`."""
    try:
        payload = part.get_payload(decode=True)
        if not isinstance(payload, (bytes, bytearray)):
            return ""
        codificacion = part.get_content_charset() or "utf-8"
        return bytes(payload).decode(codificacion, errors="replace")
    except (LookupError, UnicodeDecodeError) as exc:
        problemas.append(f"codificación inválida: {exc}")
        crudo = part.get_payload(decode=True)
        if not isinstance(crudo, (bytes, bytearray)):
            return ""
        return bytes(crudo).decode("utf-8", errors="replace")


def _procesar_parte(part: Message, cuerpo: CorreoBruto, nivel: int) -> None:
    """Procesa una parte (hoja o contenedor) y llena `cuerpo`.

    Maneja mensajes single-part y multipart por igual (AC-NORM-06: un correo
    de cuerpo vacío no debe lanzar, solo quedar degradado).
    """
    if nivel > cuerpo.profundidad_mime:
        cuerpo.profundidad_mime = nivel
    if part.is_multipart():
        for sub in part.get_payload():
            if isinstance(sub, Message):
                _procesar_parte(sub, cuerpo, nivel + 1)
        return
    # Primero la disposición: un adjunto text/plain NO es cuerpo (FR-001).
    if part.get_content_disposition() == "attachment":
        crudo = part.get_payload(decode=True)
        payload = crudo if isinstance(crudo, (bytes, bytearray)) else b""
        nombre = part.get_filename() or "adjunto_sin_nombre"
        cuerpo.adjuntos_crudos.append((nombre, part.get_content_type(), bytes(payload)))
        return
    if (
        part.get_content_maintype() == "text"
        and part.get_content_subtype() in ("html", "plain")
    ):
        texto = _decodificar_parte(part, cuerpo.problemas)
        if part.get_content_subtype() == "html":
            cuerpo.cuerpo_html += texto
        else:
            cuerpo.cuerpo_texto += texto


def parsear_mensaje(msg: Message, bytes_totales: int) -> CorreoBruto:
    """Convierte un mensaje `email` ya parseado en `CorreoBruto`.

    Args:
        msg: mensaje de la biblioteca estándar (policy.default).
        bytes_totales: longitud en bytes de la entrada cruda (para el límite).

    Returns:
        CorreoBruto con cabeceras, cuerpos, adjuntos y profundidad.
    """
    cuerpo = CorreoBruto(bytes_totales=bytes_totales)
    cuerpo.cabeceras = _extraer_cabeceras(msg)
    _procesar_parte(msg, cuerpo, nivel=1)
    return cuerpo


def parsear_bytes(raw: bytes) -> CorreoBruto:
    """Parsea bytes crudos (Gmail raw o `.eml`) a `CorreoBruto` sin excepciones no controladas.

    Args:
        raw: bytes crudos del mensaje.

    Returns:
        CorreoBruto; si la entrada es vacía o inparseable, devuelve uno
        degradado con `problemas` poblados (AC-NORM-06).
    """
    cuerpo = CorreoBruto(bytes_totales=len(raw))
    if not raw:
        cuerpo.problemas.append("entrada vacía")
        return cuerpo
    try:
        msg = email.message_from_bytes(raw, policy=policy.default)
    except (email.errors.MessageError, AttributeError, TypeError) as exc:
        cuerpo.problemas.append(f"no parseable: {exc}")
        return cuerpo
    return parsear_mensaje(msg, len(raw))
