"""Pipeline de normalización de correos (spec 002, FR-001..FR-005).

Convierte cualquier entrada (Gmail crudo, `.eml`, payload de API) en un
`EmailData` ampliado, acotado y saneado. API pública (contrato en
`specs/002-normalizacion-correo/contracts/normalizacion-api.md`):

- ``normalizar_desde_gmail`` / ``normalizar_desde_eml`` / ``normalizar_desde_api``
- ``enmascarar_para_terceros`` / ``enmascarar_texto``

Garantías: sin red, sin escritura a disco, determinismo (Art. II.5/V.5).
Las entradas malformadas degradan con ``ENTRADA_DEGRADADA`` en vez de lanzar
(AC-NORM-06).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from src.level2_agent.models import Cabecera, EmailData
from src.level2_agent.normalizacion.enmascarado import (
    enmascarar_para_terceros,
    enmascarar_texto,
)
from src.level2_agent.normalizacion.extraccion import extraer_adjuntos, extraer_urls
from src.level2_agent.normalizacion.html_a_texto import html_a_texto
from src.level2_agent.normalizacion.limites import (
    BANDERA_ENTRADA_DEGRADADA,
    BANDERA_LIMITE_EXCEDIDO,
    LIMITE_ADJUNTOS,
    LIMITE_BYTES_CORREO,
    LIMITE_CARACTERES_TEXTO,
    LIMITE_NIVELES_MIME,
    LIMITE_URLS,
    TEXTO_OCULTO_MARCADOR,
    ResultadoLimites,
    evaluar_limites,
)
from src.level2_agent.normalizacion.parseo_mime import CorreoBruto, parsear_bytes

__all__ = [
    "BANDERA_ENTRADA_DEGRADADA",
    "BANDERA_LIMITE_EXCEDIDO",
    "LIMITE_ADJUNTOS",
    "LIMITE_BYTES_CORREO",
    "LIMITE_CARACTERES_TEXTO",
    "LIMITE_NIVELES_MIME",
    "LIMITE_URLS",
    "TEXTO_OCULTO_MARCADOR",
    "enmascarar_para_terceros",
    "enmascarar_texto",
    "normalizar_desde_api",
    "normalizar_desde_eml",
    "normalizar_desde_gmail",
]


def _primera_cabecera(cabeceras: list[Cabecera], nombre: str) -> str:
    """Devuelve el valor de la primera cabecera con ese nombre (insensible a mayúsculas)."""
    nombre = nombre.lower()
    for cab in cabeceras:
        if cab.nombre.lower() == nombre:
            return cab.valor
    return ""


def _destinatario_limpio(to_crudo: str) -> str:
    """Extrae la dirección del destinatario de un valor `To` con nombre visible."""
    to_crudo = to_crudo.strip()
    if "<" in to_crudo:
        return to_crudo.split("<")[-1].split(">")[0].strip()
    return to_crudo


def _headers_legado(cabeceras: list[Cabecera]) -> str:
    """Deriva el campo legacy `headers` (JSON string) de `cabeceras`.

    Conserva la primera aparición de cada clave (legado/genético solo lee la
    primera). La fuente de verdad ordenada y con repetidas es `cabeceras`.

    Auditoría AUD-02: era `str(vistos)` (repr de Python, comillas simples);
    `json.loads` fallaba en todos los consumidores. Ahora es JSON válido.
    """
    vistos: dict[str, str] = {}
    for cab in cabeceras:
        clave = cab.nombre.lower()
        if clave not in vistos:
            vistos[clave] = cab.valor
    return json.dumps(vistos)


def _texto_para_llm(correo: CorreoBruto) -> str:
    """Combina el HTML saneado y la parte `text/plain` en el texto a analizar."""
    desde_html = html_a_texto(correo.cuerpo_html)
    plano = correo.cuerpo_texto.strip()
    partes = [p for p in (desde_html, plano) if p]
    return "\n\n".join(partes)


def _recolectar_banderas(
    correo: CorreoBruto, res: ResultadoLimites
) -> tuple[list[str], list[str]]:
    """Acumula banderas (límites + degradación) y sus detalles (SC-003).

    Args:
        correo: el correo crudo parseado.
        res: resultado del acotamiento por límites.

    Returns:
        Tupla (banderas, detalles); vacías si el correo es sano.
    """
    banderas: list[str] = []
    detalles: list[str] = []
    if res.bandera is not None:
        banderas.append(res.bandera)
        detalles.extend(res.detalles)
    # Degradación: vacío, sin cabeceras, sin cuerpo o con problemas de parseo.
    sin_cabeceras = not correo.cabeceras
    sin_cuerpo = not correo.cuerpo_html and not correo.cuerpo_texto
    if correo.problemas or sin_cabeceras or sin_cuerpo:
        banderas.append(BANDERA_ENTRADA_DEGRADADA)
        detalles.extend(correo.problemas)
    return banderas, detalles


def _ensamblar(
    correo: CorreoBruto,
    origen: Literal["gmail", "api"],
    message_id: str,
) -> EmailData:
    """Construye el `EmailData` final desde un `CorreoBruto` (sin enmascarar)."""
    texto_limpio = _texto_para_llm(correo)
    urls = extraer_urls(correo.cuerpo_html, correo.cuerpo_texto)
    adjuntos = extraer_adjuntos(correo.adjuntos_crudos)

    res = evaluar_limites(
        correo.bytes_totales, texto_limpio, urls, adjuntos, correo.profundidad_mime
    )
    banderas, detalles = _recolectar_banderas(correo, res)

    return EmailData(
        htmlBody=correo.cuerpo_html,
        headers=_headers_legado(correo.cabeceras),
        subject=_primera_cabecera(correo.cabeceras, "subject"),
        recipient=_destinatario_limpio(_primera_cabecera(correo.cabeceras, "to")),
        textBody=correo.cuerpo_texto,
        message_id=message_id,
        cabeceras=correo.cabeceras,
        texto_limpio=res.texto_limpio,
        urls=list(res.urls),
        adjuntos=list(res.adjuntos),
        origen=origen,
        banderas=banderas,
        revision_manual=bool(banderas),
    )


def _message_id_desde_correo(correo: CorreoBruto, contenido: bytes) -> str:
    """Obtiene el `Message-ID` de la cabecera o lo genera determinista (sha256[:16])."""
    cabecera = _primera_cabecera(correo.cabeceras, "message-id")
    if cabecera:
        return cabecera
    return hashlib.sha256(contenido).hexdigest()[:16]


def normalizar_desde_gmail(raw_bytes: bytes, message_id: str) -> EmailData:
    """Normaliza un correo crudo de Gmail (`format="raw"` ya decodificado).

    Args:
        raw_bytes: bytes crudos del mensaje (Base64 url-safe ya decodificado).
        message_id: ID del mensaje en Gmail.

    Returns:
        `EmailData` con `origen="gmail"` y todos los campos poblados.
        Entradas malformadas degradan con `ENTRADA_DEGRADADA` (AC-NORM-06).

    Raises:
        TypeError: si `raw_bytes` no es `bytes`.
    """
    if not isinstance(raw_bytes, bytes):
        raise TypeError("raw_bytes debe ser bytes")
    correo = parsear_bytes(raw_bytes)
    return _ensamblar(correo, "gmail", message_id)


def normalizar_desde_eml(contenido: bytes) -> EmailData:
    """Normaliza el contenido de un archivo `.eml`.

    Args:
        contenido: bytes del archivo `.eml`.

    Returns:
        `EmailData` con `origen="api"`; `message_id` de la cabecera o
        determinista (`sha256[:16]`) si falta.

    Raises:
        TypeError: si `contenido` no es `bytes`.
    """
    if not isinstance(contenido, bytes):
        raise TypeError("contenido debe ser bytes")
    correo = parsear_bytes(contenido)
    message_id = _message_id_desde_correo(correo, contenido)
    return _ensamblar(correo, "api", message_id)


def _correo_desde_payload(payload: dict[str, Any]) -> CorreoBruto:
    """Construye un `CorreoBruto` desde los campos de un payload de API (sin `raw`)."""
    cuerpo = CorreoBruto()
    headers = payload.get("headers") or {}
    if isinstance(headers, dict):
        for nombre, valor in headers.items():
            cuerpo.cabeceras.append(Cabecera(nombre=str(nombre), valor=str(valor)))
    if payload.get("subject"):
        cuerpo.cabeceras.append(Cabecera(nombre="Subject", valor=str(payload["subject"])))
    if payload.get("from"):
        cuerpo.cabeceras.append(Cabecera(nombre="From", valor=str(payload["from"])))
    if payload.get("to"):
        cuerpo.cabeceras.append(Cabecera(nombre="To", valor=str(payload["to"])))
    cuerpo.cuerpo_texto = str(payload.get("text") or "")
    cuerpo.cuerpo_html = str(payload.get("html") or "")
    cuerpo.bytes_totales = len(cuerpo.cuerpo_texto) + len(cuerpo.cuerpo_html)
    return cuerpo


def normalizar_desde_api(payload: dict[str, Any]) -> EmailData:
    """Normaliza un payload JSON de la futura API (formato provisional, spec 12).

    Args:
        payload: diccionario con claves opcionales `raw`, `subject`, `from`,
            `to`, `text`, `html`, `headers`. Con `raw` usa el camino MIME;
            sin él, construye desde los campos.

    Returns:
        `EmailData` con `origen="api"`. Payload sin ningún campo útil degrada
        con `ENTRADA_DEGRADADA`.

    Raises:
        TypeError: si `payload` no es un diccionario.
    """
    if not isinstance(payload, dict):
        raise TypeError("payload debe ser un dict")
    raw = payload.get("raw")
    if isinstance(raw, str) and raw:
        import base64

        try:
            contenido = base64.urlsafe_b64decode(raw.encode("ASCII"))
        except (ValueError, TypeError):
            contenido = raw.encode("utf-8", errors="replace")
        correo = parsear_bytes(contenido)
        message_id = _message_id_desde_correo(correo, contenido)
        return _ensamblar(correo, "api", message_id)
    correo = _correo_desde_payload(payload)
    message_id = str(payload.get("message_id") or "")
    return _ensamblar(correo, "api", message_id)
