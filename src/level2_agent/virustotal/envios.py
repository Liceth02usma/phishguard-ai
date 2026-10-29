"""Flujos de envío detrás de flags (spec 006, FR-008, research D13).

`subir_archivo` (`POST /files`) y `enviar_url_desconocida` (`POST /urls` +
`GET /analyses/{id}`) solo emiten petición si `VT_UPLOAD_UNKNOWN` /
`VT_SUBMIT_UNKNOWN_URLS` están activos (default `false`): con los flags
apagados cortan ANTES de armar la petición → cero POST (AC-VT-09, G10).
Se separaron de `cliente.py` por el límite de 500 líneas (Art. III.1).
"""

from __future__ import annotations

import asyncio
import logging

from src.level2_agent.virustotal.configuracion import ConfigVT
from src.level2_agent.virustotal.identificadores import (
    normalizar_sha256,
    sanitizar_url,
    validar_url,
)
from src.level2_agent.virustotal.modelos import (
    ESPERA_ANALISIS_URL_SEGUNDOS,
    TOPE_CONSULTAS_ANALISIS_URL,
)
from src.level2_agent.virustotal.puertos import (
    DependenciasVT,
    dependencias_por_defecto,
)

logger = logging.getLogger(__name__)


def subir_archivo(
    sha256: str,
    contenido: bytes,
    *,
    config: ConfigVT | None = None,
    deps: DependenciasVT | None = None,
) -> bool:
    """`POST /files` SOLO con `VT_UPLOAD_UNKNOWN=true` (FR-008, D13, AC-VT-09).

    Con el flag apagado corta antes de armar la petición: cero POST. No
    consume ficha de presupuesto (es decisión explícita del operador) y
    respeta la clave y el cortacircuitos.
    """
    cfg = config if config is not None else ConfigVT.desde_entorno()
    if not cfg.upload_unknown:
        logger.info("subir_archivo desactivada (VT_UPLOAD_UNKNOWN=false): sin petición (FR-008)")
        return False
    if normalizar_sha256(sha256) is None or not contenido:
        return False
    return asyncio.run(_subir_async(sha256.lower(), contenido, cfg=cfg, deps=deps))


def enviar_url_desconocida(
    url: str,
    *,
    config: ConfigVT | None = None,
    deps: DependenciasVT | None = None,
) -> bool:
    """`POST /urls` SOLO con `VT_SUBMIT_UNKNOWN_URLS=true` (FR-008, D13, AC-VT-09).

    Con el flag apagado corta antes de armar la petición: cero POST.
    """
    cfg = config if config is not None else ConfigVT.desde_entorno()
    if not cfg.submit_unknown_urls:
        logger.info(
            "enviar_url_desconocida desactivada (VT_SUBMIT_UNKNOWN_URLS=false): sin petición"
        )
        return False
    if validar_url(url) is None:
        return False
    return asyncio.run(_enviar_flow(sanitizar_url(url), cfg=cfg, deps=deps))


async def enviar_url_async(url_saneada: str, dp: DependenciasVT) -> bool:
    """`POST /urls` + `GET /analyses/{id}` máx. 3 con 5 s de espaciado (M06.2).

    Lo usa `cliente._desde_404` cuando `VT_SUBMIT_UNKNOWN_URLS=true`.
    """
    respuesta = await dp.cliente.post("/urls", json={"url": url_saneada})
    if respuesta.status not in (200, 409):
        logger.warning("POST /urls devolvió HTTP %s: URL no enviada", respuesta.status)
        return False
    identificador = str(respuesta.json.get("data", {}).get("id", ""))
    for _ in range(TOPE_CONSULTAS_ANALISIS_URL):
        await dp.dormir(ESPERA_ANALISIS_URL_SEGUNDOS)
        estado = await dp.cliente.get(f"/analyses/{identificador}")
        atributos = estado.json.get("data", {}).get("attributes", {})
        if atributos.get("status") == "completed":
            return True
    logger.info(
        "URL enviada pero sin completar en %s consultas de análisis (M06.2)",
        TOPE_CONSULTAS_ANALISIS_URL,
    )
    return False


async def _subir_async(
    sha256: str, contenido: bytes, *, cfg: ConfigVT, deps: DependenciasVT | None
) -> bool:
    """`POST /files` crudo con la clave construida solo en la petición (FR-008/D10)."""
    dp = deps if deps is not None else dependencias_por_defecto()
    if not cfg.api_key or dp.cortacircuito.esta_abierto():
        return False
    respuesta = await dp.cliente.post("/files", content=contenido)
    return respuesta.status == 200


async def _enviar_flow(url_saneada: str, *, cfg: ConfigVT, deps: DependenciasVT | None) -> bool:
    """Valida estado previo y delega en el envío detrás del flag (FR-008)."""
    dp = deps if deps is not None else dependencias_por_defecto()
    if not cfg.api_key or dp.cortacircuito.esta_abierto():
        return False
    return await enviar_url_async(url_saneada, dp)
