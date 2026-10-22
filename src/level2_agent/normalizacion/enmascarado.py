"""Enmascarado de datos personales antes de persistir o enviar a terceros (FR-005).

Correos electrónicos → `j***@empresa.com` (primera letra del local + `***` +
dominio). Secuencias de 13 a 19 dígitos (con espacios o guiones opcionales) →
`[NÚMERO_OCULTO]`. El remitente (cabecera `From`) NO se enmascara (excepción
FR-005). Funciones puras e idempotentes.
"""

from __future__ import annotations

import re

from src.level2_agent.models import Cabecera, EmailData

# Un correo: local (1+ de la clase) @ dominio.tld (TLD >= 2 letras).
CORREO_PATRON = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
# Detector de correos (para comprobar ausencia tras enmascarar).
CONTIENE_CORREO = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Secuencia de >=13 digitos con separadores opcionales (13 a 19+ digitos).
DIGITOS_PATRON = re.compile(r"\d(?:[\s-]*\d){12,}")
# Detector de secuencias largas de digitos (para comprobar ausencia tras enmascarar).
CONTIENE_DIGITOS_LARGOS = DIGITOS_PATRON

_REMPLAZO_CORREO = r"\1***@\2"
_REMPLAZO_DIGITOS = "[NÚMERO_OCULTO]"


def enmascarar_texto(texto: str) -> str:
    """Enmascara correos y secuencias de 13+ dígitos en una cadena.

    Args:
        texto: cadena a saneado (puede ser vacía).

    Returns:
        La cadena con correos y números personales enmascarados; idempotente.
    """
    if not texto:
        return ""
    sin_correos = CORREO_PATRON.sub(_REMPLAZO_CORREO, texto)
    return DIGITOS_PATRON.sub(_REMPLAZO_DIGITOS, sin_correos)


def enmascarar_para_terceros(email_data: EmailData) -> EmailData:
    """Devuelve una copia de `email_data` con la PII enmascarada para terceros.

    Enmascara `subject`, `recipient`, `textBody`, `texto_limpio`, `htmlBody`,
    `headers`, las URLs y los nombres de adjuntos; conserva intacta la cabecera
    `From` (remitente) y los identificadores (`message_id`, `origen`, hashes).
    El texto que ve el modelo (`subject`, `htmlBody`, `headers`) se enmascara
    primero y luego se trunca a su cuota, de modo que el total nunca excede
    `LIMITE_CARACTERES_TEXTO` (Art. 0.6 / FR-004).

    Args:
        email_data: correo normalizado (o legado).

    Returns:
        Una copia nueva con la vista apta para el LLM y la persistencia
        (AC-NORM-04). El objeto original no se modifica.
    """
    from src.level2_agent.normalizacion.limites import (
        LIMITE_ASUNTO_LLM,
        LIMITE_HEADERS_LLM,
        LIMITE_HTML_LLM,
    )

    copia = email_data.model_copy()
    copia.subject = enmascarar_texto(email_data.subject)[:LIMITE_ASUNTO_LLM]
    copia.recipient = enmascarar_texto(email_data.recipient)
    copia.textBody = enmascarar_texto(email_data.textBody)
    copia.texto_limpio = enmascarar_texto(email_data.texto_limpio)
    copia.htmlBody = enmascarar_texto(email_data.htmlBody)[:LIMITE_HTML_LLM]
    copia.headers = enmascarar_texto(email_data.headers)[:LIMITE_HEADERS_LLM]
    copia.cabeceras = [
        c
        if c.nombre.lower() == "from"
        else Cabecera(nombre=c.nombre, valor=enmascarar_texto(c.valor))
        for c in email_data.cabeceras
    ]
    copia.urls = [enmascarar_texto(u) for u in email_data.urls]
    copia.adjuntos = [
        a.model_copy(update={"nombre": enmascarar_texto(a.nombre)}) for a in email_data.adjuntos
    ]
    return copia
