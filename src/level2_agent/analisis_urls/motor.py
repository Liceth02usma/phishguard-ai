"""Orquestador del análisis de URLs (spec 004): extraer → normalizar → expandir → bandear.

Sin wiring al pipeline (research D11): la API es consumida por las specs
006/007/008. Todas las fallas externas degradan a `error_controlado` con
motivo acotado (III.9, AC-URL-07 / I6).
"""

from __future__ import annotations

from src.level2_agent.analisis_urls.banderas import evaluar_banderas_url
from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.extraccion import extraer_candidatas
from src.level2_agent.analisis_urls.expansion import expandir_acortador
from src.level2_agent.analisis_urls.modelos import (
    CodigoBandaURL,
    EstadisticasURLs,
    ResultadoExpansion,
    ResultadoURLs,
    UrlAnalizada,
    bandera,
)
from src.level2_agent.analisis_urls.normalizacion import (
    UrlNormalizada,
    esquema_de,
    host_de,
    normalizar_y_deduplicar,
)
from src.level2_agent.analisis_urls.puertos import DependenciasURLs, dependencias_por_defecto
from src.level2_agent.analisis_urls.sanitizacion import sanitizar_parametros
from src.level2_agent.models import EmailData


def _dominio_base(host: str) -> str:
    """Dominio base (2 últimas etiquetas) para consultar la antigüedad una sola vez."""
    etiquetas = [etiqueta for etiqueta in host.split(".") if etiqueta]
    if len(etiquetas) < 2:
        return host
    return ".".join(etiquetas[-2:])


def _edad_del_dominio(host: str, deps: DependenciasURLs, cache: dict[str, int | None]) -> int | None:
    """Edad vía RDAP, consultada UNA vez por dominio y degradando a None (D5)."""
    if not host:
        return None
    dominio = _dominio_base(host)
    if dominio not in cache:
        try:
            cache[dominio] = deps.rdap.antiguedad_dias(dominio)
        except Exception:  # noqa: BLE001 — puerto externo: desconocido ≠ nuevo (V.1)
            cache[dominio] = None
    return cache[dominio]


def _detalle_de(codigo: CodigoBandaURL, url: UrlAnalizada, edad: int | None) -> str:
    """Detalle sin PII: solo host, estado y contadores (Art. V.4, D12)."""
    if codigo == "URL_DOMINIO_NUEVO":
        return f"URL_DOMINIO_NUEVO: dominio con {edad} dias (< 30)"
    if codigo == "REDIRECCION_EXCESIVA" and url.expansion is not None:
        return (
            f"REDIRECCION_EXCESIVA: {url.expansion.estado} tras {url.expansion.saltos} saltos"
        )
    return f"{codigo} en {url.host or '(host no parseable)'}"


def _analizar_una(
    item: UrlNormalizada,
    config: ConfigURLs,
    deps: DependenciasURLs,
    edades: dict[str, int | None],
) -> UrlAnalizada:
    """Analiza una URL: saneado, expansión (solo acortadoras) y banderas."""
    host = host_de(item.normalizada)
    esquema = esquema_de(item.normalizada)
    es_acortadora = host in config.acortadores
    url_saneada = sanitizar_parametros(item.normalizada, config)

    expansion: ResultadoExpansion | None = None
    if es_acortadora:
        try:
            expansion = expandir_acortador(url_saneada, config, deps)
        except Exception:  # noqa: BLE001 — última red de seguridad (III.9, I6)
            expansion = ResultadoExpansion(estado="error_controlado", motivo="fallo_inesperado")

    url = UrlAnalizada(
        original=item.original,
        normalizada=item.normalizada,
        host=host,
        esquema=esquema,
        texto_mostrado=item.texto,
        es_acortadora=es_acortadora,
        url_saneada=url_saneada,
        expansion=expansion,
    )
    edad = _edad_del_dominio(host, deps, edades)
    url.codigos = evaluar_banderas_url(url, config, expansion, edad)
    return url


def _estadisticas(urls: list[UrlAnalizada]) -> EstadisticasURLs:
    """Contadores coherentes: cada URL cuenta exactamente una vez."""
    expandidas = sum(
        1 for u in urls if u.expansion is not None and u.expansion.estado == "expandida"
    )
    bloqueadas = sum(
        1 for u in urls if u.expansion is not None and u.expansion.estado == "bloqueada_ssrf"
    )
    return EstadisticasURLs(
        total=len(urls),
        expandidas=expandidas,
        bloqueadas_ssrf=bloqueadas,
        sin_expansion=len(urls) - expandidas - bloqueadas,
    )


def analizar_urls(
    email_data: EmailData,
    config: ConfigURLs | None = None,
    deps: DependenciasURLs | None = None,
) -> ResultadoURLs:
    """Analiza todas las URLs del correo (contrato: contracts/analizar-urls.md).

    `config=None` lee el entorno; `deps=None` usa las implementaciones de
    producción (D4–D7). Ninguna entrada del correo provoca excepción (I6).
    """
    config_efectiva = ConfigURLs.desde_entorno() if config is None else config
    deps_efectivas = dependencias_por_defecto() if deps is None else deps

    html = email_data.htmlBody or ""
    texto = email_data.textBody or email_data.texto_limpio or ""
    candidatas = extraer_candidatas(html, texto)
    normalizadas = normalizar_y_deduplicar(candidatas, config_efectiva)

    edades: dict[str, int | None] = {}
    urls = [_analizar_una(item, config_efectiva, deps_efectivas, edades) for item in normalizadas]
    banderas = [
        bandera(codigo, _detalle_de(codigo, url, edades.get(_dominio_base(url.host))))
        for url in urls
        for codigo in url.codigos
    ]
    return ResultadoURLs(urls=urls, banderas=banderas, estadisticas=_estadisticas(urls))
