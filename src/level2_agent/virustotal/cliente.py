"""Cliente síncrono de VirusTotal API v3 (spec 006, módulo M06).

Orquesta FR-001..FR-009: validación → caché → clave → cortacircuitos → cuota
diaria → presupuesto (si lo comparte el consumidor) → cubeta de minuto →
`GET` con reintentos → clasificación (M06.4) → caché SOLO de veredictos
reales (clarify FR-005: los transitorios jamás se cachean). API síncrona (D2)
sobre dependencias asíncronas; el saneado de URLs delega en la spec 004 (D7);
`models.py` no se toca. La clave se construye solo en la petición (D10/FR-009).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from src.level2_agent.virustotal.cache import clave_cache, ttl_para
from src.level2_agent.virustotal.clasificacion import clasificar_stats
from src.level2_agent.virustotal.configuracion import ConfigVT
from src.level2_agent.virustotal.envios import enviar_url_async
from src.level2_agent.virustotal.identificadores import (
    id_url_base64,
    normalizar_sha256,
    sanitizar_url,
    validar_dominio,
    validar_ip,
    validar_url,
)
from src.level2_agent.virustotal.modelos import (
    BanderaVT,
    Clasificacion,
    EntradaCache,
    FuenteVT,
    LastAnalysisStats,
    ResultadoVT,
    TipoIndicador,
    bandera,
)
from src.level2_agent.virustotal.presupuesto import Presupuesto
from src.level2_agent.virustotal.puertos import (
    DependenciasVT,
    RespuestaVT,
    dependencias_por_defecto,
)
from src.level2_agent.virustotal.resiliencia import reintentar

logger = logging.getLogger(__name__)

_IDENTIFICADOR_INVALIDO = "<malformado>"
"""Identificador sintético para entradas inválidas (nunca se replica la entrada cruda)."""


# --- API pública síncrona (contrato §1) ---


def consultar_archivo(
    sha256: str,
    *,
    config: ConfigVT | None = None,
    deps: DependenciasVT | None = None,
    presupuesto: Presupuesto | None = None,
) -> ResultadoVT:
    """Clasifica un archivo por SHA-256 (FR-001, M06.2 `GET /files/{id}`)."""
    return _consultar("archivo", sha256, config=config, deps=deps, presupuesto=presupuesto)


def consultar_url(
    url: str,
    *,
    config: ConfigVT | None = None,
    deps: DependenciasVT | None = None,
    presupuesto: Presupuesto | None = None,
    es_riesgosa: bool = False,
) -> ResultadoVT:
    """Clasifica una URL saneada → identificador Base64 (FR-001, `GET /urls/{id}`).

    `es_riesgosa` solo alimenta el detalle del presupuesto: la prioridad real
    vive en el orden del wiring 007/008 (contrato §1, G8).
    """
    if es_riesgosa:
        logger.debug("consulta de URL marcada como riesgosa (prioridad 2 en el wiring)")
    return _consultar("url", url, config=config, deps=deps, presupuesto=presupuesto)


def consultar_dominio(
    dominio: str,
    *,
    config: ConfigVT | None = None,
    deps: DependenciasVT | None = None,
    presupuesto: Presupuesto | None = None,
) -> ResultadoVT:
    """Clasifica un dominio (FR-001, M06.2 `GET /domains/{dominio}`)."""
    return _consultar("dominio", dominio, config=config, deps=deps, presupuesto=presupuesto)


def consultar_ip(
    ip: str,
    *,
    config: ConfigVT | None = None,
    deps: DependenciasVT | None = None,
    presupuesto: Presupuesto | None = None,
) -> ResultadoVT:
    """Clasifica una IP (FR-001, M06.2 `GET /ip_addresses/{ip}`)."""
    return _consultar("ip", ip, config=config, deps=deps, presupuesto=presupuesto)


# --- Núcleo asíncrono envuelto en síncrono (D2) ---


def _consultar(
    tipo: TipoIndicador,
    valor: str,
    *,
    config: ConfigVT | None,
    deps: DependenciasVT | None,
    presupuesto: Presupuesto | None,
) -> ResultadoVT:
    """Envuelve el flujo asíncrono (D2: API síncrona).

    Si ya hay un event loop corriendo (ej. uvicorn), ejecuta la corrutina
    en un thread dedicado con su propio loop. No se anida asyncio.run()
    sobre el loop activo (nest_asyncio parchea el loop del servidor y rompe
    el seguimiento de trazas de herramientas como coverage).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Sin loop activo: asyncio.run directo
        return asyncio.run(
            _consultar_async(tipo, valor, config=config, deps=deps, presupuesto=presupuesto)
        )

    # Hay un loop corriendo: thread dedicado con su propio loop
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            asyncio.run,
            _consultar_async(tipo, valor, config=config, deps=deps, presupuesto=presupuesto),
        )
        return future.result()


async def _consultar_async(
    tipo: TipoIndicador,
    valor: str,
    *,
    config: ConfigVT | None,
    deps: DependenciasVT | None,
    presupuesto: Presupuesto | None,
) -> ResultadoVT:
    """Resuelve dependencias y ejecuta el flujo; cierra el cliente si fue propio."""
    cfg = config if config is not None else ConfigVT.desde_entorno()
    dp = deps if deps is not None else dependencias_por_defecto()
    propias = deps is None
    try:
        return await _flujo(tipo, valor, cfg=cfg, dp=dp, presupuesto=presupuesto)
    finally:
        if propias:
            cierre = getattr(dp.cliente, "cerrar", None)
            if callable(cierre):
                await cierre()


async def _flujo(
    tipo: TipoIndicador,
    valor: str,
    *,
    cfg: ConfigVT,
    dp: DependenciasVT,
    presupuesto: Presupuesto | None,
) -> ResultadoVT:
    """Valida, consulta caché y orquesta cuota/presupuesto/reintentos (III.2)."""
    identificador = _normalizar(tipo, valor)
    if identificador is None:
        return _sin_llamada(
            tipo, _IDENTIFICADOR_INVALIDO, "VT_DESCONOCIDO",
            "indicador inválido: sin llamada a VirusTotal (G12)",
        )
    clave = clave_cache(tipo, identificador)
    ahora = dp.reloj()
    entrada = dp.cache.obtener(clave, ahora)
    if entrada is not None:
        return _desde_cache(tipo, identificador, entrada, cfg)
    if not cfg.api_key:
        return _sin_llamada(
            tipo, identificador, "VT_NO_DISPONIBLE", "VT_API_KEY ausente: sin red (FR-009)"
        )
    if dp.cortacircuito.esta_abierto():
        return _sin_llamada(
            tipo, identificador, "VT_NO_DISPONIBLE", "cortacircuitos abierto (FR-004)"
        )
    dia = ahora.strftime("%Y-%m-%d")
    if cfg.tope_dia > 0 and dp.contador.usos(dia) >= cfg.tope_dia:
        return _sin_llamada(
            tipo, identificador, "VT_NO_DISPONIBLE", "cuota diaria agotada (FR-002)"
        )
    if presupuesto is not None and not presupuesto.usar():
        return _sin_llamada(
            tipo, identificador, "VT_PRESUPUESTO_AGOTADO", "presupuesto por correo agotado (FR-006)"
        )
    await dp.limitador.esperar_ficha(cfg.rpm)
    if not dp.contador.consumir(dia):
        return _sin_llamada(
            tipo, identificador, "VT_NO_DISPONIBLE", "cuota diaria agotada (FR-002)"
        )
    respuesta = await _consultar_e_interpretar(tipo, identificador, valor, cfg=cfg, dp=dp)
    return respuesta


async def _consultar_e_interpretar(
    tipo: TipoIndicador,
    identificador: str,
    valor: str,
    *,
    cfg: ConfigVT,
    dp: DependenciasVT,
) -> ResultadoVT:
    """Ejecuta el GET con reintentos y convierte la respuesta (FR-003, M06.4)."""
    ruta = _ruta(tipo, identificador)

    async def accion() -> RespuestaVT:
        return await dp.cliente.get(ruta)

    respuesta = await reintentar(accion, reloj=dp.reloj, dormir=dp.dormir, jitter=dp.jitter)
    return await _interpretar(tipo, identificador, valor, cfg, dp, respuesta)


async def _interpretar(
    tipo: TipoIndicador,
    identificador: str,
    valor: str,
    cfg: ConfigVT,
    dp: DependenciasVT,
    respuesta: RespuestaVT | None,
) -> ResultadoVT:
    """Convierte la respuesta HTTP en `ResultadoVT` + flags de catálogo (M06.4)."""
    ahora = dp.reloj()
    if respuesta is None or respuesta.status == 429 or respuesta.status >= 500:
        dp.cortacircuito.registrar_fallo()
        causa = (
            "error de transporte" if respuesta is None else f"HTTP {respuesta.status} persistente"
        )
        return _resultado(
            tipo,
            identificador,
            "desconocida",
            "red",
            [bandera("VT_DESCONOCIDO", f"{causa} tras reintentos; desconocida, nunca limpia")],
            None,
            1,
        )
    dp.cortacircuito.registrar_exito()
    if respuesta.status == 404:
        return await _desde_404(tipo, identificador, valor, clave_cache(tipo, identificador),
                                cfg, dp, ahora)
    if respuesta.status != 200:
        return _resultado(
            tipo,
            identificador,
            "desconocida",
            "red",
            [bandera("VT_DESCONOCIDO", f"HTTP {respuesta.status} sin veredicto; desconocida")],
            None,
            1,
        )
    stats = _extraer_stats(respuesta.json)
    if stats is None:
        return _resultado(
            tipo,
            identificador,
            "desconocida",
            "red",
            [bandera("VT_DESCONOCIDO", "respuesta 200 sin last_analysis_stats; desconocida")],
            None,
            1,
        )
    clasificacion = clasificar_stats(stats, cfg)
    dp.cache.guardar(
        EntradaCache(
            clave=clave_cache(tipo, identificador),
            clasificacion=clasificacion,
            stats=stats,
            guardada_en=ahora,
            expira_en=ahora + ttl_para(tipo),
        )
    )
    banderas = _banderas_veredicto(tipo, clasificacion, stats)
    if clasificacion == "desconocida":
        banderas = [
            *banderas,
            bandera("VT_DESCONOCIDO", "veredicto sin apoyos; desconocida, nunca limpia"),
        ]
    return _resultado(tipo, identificador, clasificacion, "red", banderas, stats, 1)


async def _desde_404(
    tipo: TipoIndicador,
    identificador: str,
    valor: str,
    clave: str,
    cfg: ConfigVT,
    dp: DependenciasVT,
    ahora: datetime,
) -> ResultadoVT:
    """404 → `desconocida` cacheada 1 h; envía solo con el flag activo (FR-005/FR-008)."""
    dp.cache.guardar(
        EntradaCache(
            clave=clave,
            clasificacion="desconocida",
            stats=None,
            guardada_en=ahora,
            expira_en=ahora + ttl_para(tipo, es_desconocido=True),
        )
    )
    if tipo == "url" and cfg.submit_unknown_urls:
        await enviar_url_async(sanitizar_url(valor), dp)
    return _resultado(
        tipo,
        identificador,
        "desconocida",
        "red",
        [bandera("VT_DESCONOCIDO", "404 de VirusTotal: desconocido, nunca limpio (FR-001)")],
        None,
        1,
    )


# --- Constructores y parsers puros ---


def _desde_cache(
    tipo: TipoIndicador,
    identificador: str,
    entrada: EntradaCache,
    cfg: ConfigVT,
) -> ResultadoVT:
    """Veredicto desde caché: reclasifica con los umbrales ACTUALES (FR-005, D12)."""
    stats = entrada.stats
    clasificacion = clasificar_stats(stats, cfg) if stats is not None else entrada.clasificacion
    banderas = _banderas_veredicto(tipo, clasificacion, stats)
    if clasificacion == "desconocida":
        banderas = [
            *banderas,
            bandera("VT_DESCONOCIDO", "desconocido desde caché: nunca limpio (FR-001)"),
        ]
    return _resultado(tipo, identificador, clasificacion, "cache", banderas, stats, 0)


def _banderas_veredicto(
    tipo: TipoIndicador, clasificacion: Clasificacion, stats: LastAnalysisStats | None
) -> list[BanderaVT]:
    """Flags de catálogo SOLO para veredictos positivos de archivo/URL (5.2/5.3).

    Dominio/IP no tienen código propio en los catálogos (Art. VI.2: no se
    inventan valores); su veredicto viaja en `clasificacion` para 007/008.
    """
    if stats is None:
        return []
    resumen = f"malicious={stats.malicious}, suspicious={stats.suspicious}"
    if tipo == "archivo" and clasificacion in ("maliciosa", "sospechosa"):
        return [
            bandera("VT_ADJ_SOSPECHOSO", f"hash clasificado '{clasificacion}' ({resumen})")
        ]
    if tipo == "url" and clasificacion == "sospechosa":
        return [
            bandera("VT_URL_SOSPECHOSA", f"url clasificada 'sospechosa' ({resumen})")
        ]
    return []


def _extraer_stats(cuerpo: dict[str, Any]) -> LastAnalysisStats | None:
    """`data.attributes.last_analysis_stats` → modelo; ausente/malformado → None."""
    try:
        crudos = cuerpo["data"]["attributes"]["last_analysis_stats"]
        return LastAnalysisStats(
            malicious=int(crudos.get("malicious", 0)),
            suspicious=int(crudos.get("suspicious", 0)),
            harmless=int(crudos.get("harmless", 0)),
            undetected=int(crudos.get("undetected", 0)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _normalizar(tipo: TipoIndicador, valor: str) -> str | None:
    """Identificador canónico o None si la entrada es inválida (G12, sin excepciones)."""
    if tipo == "archivo":
        return normalizar_sha256(valor)
    if tipo == "url":
        return id_url_base64(valor) if validar_url(valor) is not None else None
    if tipo == "dominio":
        return validar_dominio(valor)
    return validar_ip(valor)


def _ruta(tipo: TipoIndicador, identificador: str) -> str:
    """Ruta del recurso en el API v3 según el tipo (M06.2)."""
    prefijos: dict[TipoIndicador, str] = {
        "archivo": "/files",
        "url": "/urls",
        "dominio": "/domains",
        "ip": "/ip_addresses",
    }
    return f"{prefijos[tipo]}/{identificador}"


def _resultado(
    tipo: TipoIndicador,
    identificador: str,
    clasificacion: Clasificacion,
    fuente: FuenteVT,
    banderas: list[BanderaVT],
    stats: LastAnalysisStats | None,
    consultas: int,
) -> ResultadoVT:
    """Compone `ResultadoVT` (los invariantes los valida el modelo, IV1–IV4)."""
    return ResultadoVT(
        tipo=tipo,
        identificador=identificador,
        clasificacion=clasificacion,
        fuente=fuente,
        banderas=banderas,
        stats=stats,
        consultas_externas=consultas,
    )


def _sin_llamada(
    tipo: TipoIndicador, identificador: str, codigo: str, detalle: str
) -> ResultadoVT:
    """Resultado sin llamada a red: `desconocida` + flag de estado (G5, III.9)."""
    return _resultado(
        tipo, identificador, "desconocida", "sin_llamada", [bandera(codigo, detalle)], None, 0
    )
