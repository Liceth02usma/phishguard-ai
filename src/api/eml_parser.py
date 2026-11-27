"""Extracción de adjuntos y cabeceras desde archivos EML (spec 012, AC-API-02).

Usa :mod:`email` de la librería estándar para parsear MIME, extraer adjuntos
como bytes en memoria (nunca escribe a disco, Art. V.5) y resolver las
cabeceras/Subject/From/To del mensaje.
"""

from __future__ import annotations

import email
import re
from dataclasses import dataclass
from email.message import Message
from email.utils import parseaddr

MAX_ADJUNTOS_EML = 10
"""Máximo de adjuntos a extraer de un EML (Art. III.6, sin números mágicos)."""


@dataclass(frozen=True)
class AdjuntoEml:
    """Adjunto extraído de un EML (nombre, tipo declarado, payload)."""

    nombre: str
    tipo_declarado: str
    payload: bytes


@dataclass(frozen=True)
class EmlParseado:
    """Cabeceras y cuerpo resueltos de un EML.

    Antes el endpoint metía el MIME crudo en ``textBody`` y dejaba
    ``recipient``/``cabeceras`` vacíos, por lo que el mismo correo daba
    resultados distintos en modo ``pegar`` y en modo ``eml``.
    """

    asunto: str
    remitente: str
    destinatario: str
    cuerpo_texto: str
    cuerpo_html: str
    cabeceras: tuple[tuple[str, str], ...]


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


def parsear_eml(contenido: bytes) -> EmlParseado:
    """Resuelve asunto, remitente, destinatario, cuerpo y cabeceras de un EML.

    El cuerpo es ``text/plain`` si existe; si no, el ``text/html`` sin etiquetas.
    Las cabeceras se conservan como pares (nombre, valor) para poblar
    ``EmailData.cabeceras`` y que las banderas 003/004 puedan evaluarse.
    """
    msg = email.message_from_bytes(contenido)

    asunto = str(msg.get("Subject") or "").strip()
    remitente = parseaddr(str(msg.get("From") or ""))[1].strip()
    destinatario = parseaddr(str(msg.get("To") or ""))[1].strip()

    cuerpo_texto, cuerpo_html = _extraer_cuerpos(msg)

    cabeceras: list[tuple[str, str]] = []
    for nombre, valor in msg.items():
        # Se descartan solo las que viajan como campos propios del modelo;
        # From y Date se conservan porque genetic_logic las usa para
        # dominio_externo / envio_madrugada.
        if nombre.lower() in ("subject", "to", "content-type",
                              "mime-version", "content-transfer-encoding"):
            continue
        valor_limpio = " ".join(str(valor).split())
        if valor_limpio:
            cabeceras.append((nombre, valor_limpio))

    if not asunto:
        asunto = "(sin asunto)"

    return EmlParseado(
        asunto=asunto,
        remitente=remitente or "(desconocido)",
        destinatario=destinatario,
        cuerpo_texto=cuerpo_texto,
        cuerpo_html=cuerpo_html,
        cabeceras=tuple(cabeceras),
    )


def _extraer_cuerpos(msg: Message) -> tuple[str, str]:
    """Devuelve (texto plano, html) del cuerpo del mensaje."""
    texto = ""
    html = ""
    if msg.is_multipart():
        for parte in msg.walk():
            if parte.is_multipart():
                continue
            tipo = parte.get_content_type()
            if tipo == "text/plain" and not texto:
                texto = _decodificar_parte(parte)
            elif tipo == "text/html" and not html:
                html = _decodificar_parte(parte)
    else:
        tipo = msg.get_content_type()
        datos = _decodificar_parte(msg)
        if tipo == "text/html":
            html = datos
        else:
            texto = datos
    return texto, html


def _decodificar_parte(parte: Message) -> str:
    """Decodifica una parte MIME (quoted-printable/base64) a str."""
    payload = parte.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    charset = parte.get_content_charset() or "utf-8"
    try:
        texto = payload.decode(charset, errors="replace")
    except (LookupError, TypeError):
        texto = payload.decode("utf-8", errors="replace")
    return texto.strip()


_ETIQUETAS = re.compile(r"<[^>]+>")


def quitar_etiquetas_html(html: str) -> str:
    """Elimina etiquetas HTML y colapsa espacios (para usar como texto plano)."""
    sin_tags = _ETIQUETAS.sub(" ", html)
    return " ".join(sin_tags.split())



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
    if "attachment" not in disposition and content_type.startswith("text/"):
        # Ignorar text/plain y text/html (cuerpo del correo)
        return None

    payload = parte.get_payload(decode=True)
    if not isinstance(payload, bytes) or len(payload) == 0:
        return None

    nombre = parte.get_filename() or "(sin_nombre)"
    return AdjuntoEml(nombre=nombre, tipo_declarado=content_type, payload=payload)
