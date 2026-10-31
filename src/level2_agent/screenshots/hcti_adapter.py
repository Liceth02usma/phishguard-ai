"""Adapter de HCTI (htmlcsstoimage) para generar screenshots (spec 010, D12).

generar_screenshot(html) -> str | None:
- Si HCTI_API_ID y HCTI_API_KEY están configurados, envía el HTML a la API
  y retorna la URL de la imagen PNG generada.
- Si no están configurados o el HTML está vacío, retorna None (degradación graceful).
- Si la API falla, retorna None y loguea warning (no bloquea la creación del ticket).

HCTI API: https://hcti.io/v1/image
Auth: Basic auth con HCTI_API_ID (usuario) y HCTI_API_KEY (password).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HCTI_API_URL = "https://hcti.io/v1/image"
"""Endpoint de la API de HCTI."""

HCTI_TIMEOUT_SEGUNDOS = 15.0
"""Timeout para la llamada a HCTI (no bloquea el pipeline)."""


def _credenciales_disponibles() -> bool:
    """Verifica si las credenciales HCTI están configuradas."""
    return bool(
        os.environ.get("HCTI_API_ID", "").strip()
        and os.environ.get("HCTI_API_KEY", "").strip()
    )


def generar_screenshot(html: str) -> str | None:
    """Genera un screenshot del HTML vía HCTI.

    Args:
        html: Contenido HTML del correo a capturar.

    Returns:
        URL de la imagen PNG, o None si:
        - HCTI no está configurado (credenciales ausentes)
        - El HTML está vacío
        - La API falla (degradación graceful)
    """
    if not html.strip():
        return None

    api_id = os.environ.get("HCTI_API_ID", "").strip()
    api_key = os.environ.get("HCTI_API_KEY", "").strip()

    if not api_id or not api_key:
        logger.debug("HCTI no configurado. Screenshot omitido.")
        return None

    try:
        response = httpx.post(
            HCTI_API_URL,
            auth=(api_id, api_key),
            json={"html": html},
            timeout=HCTI_TIMEOUT_SEGUNDOS,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        url = data.get("url", "")
        if url:
            logger.info("Screenshot generado: %s", url)
            return str(url)
        logger.warning("HCTI respondió sin URL de imagen.")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(
            "HCTI error HTTP %s: %s. Screenshot omitido.",
            e.response.status_code,
            e,
        )
        return None
    except httpx.TimeoutException:
        logger.warning("HCTI timeout (%ss). Screenshot omitido.", HCTI_TIMEOUT_SEGUNDOS)
        return None
    except Exception as e:
        logger.warning("HCTI error inesperado: %s. Screenshot omitido.", e)
        return None
