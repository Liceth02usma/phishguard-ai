"""Análisis y expansión de URLs (spec 004, módulo M04b).

Paquete determinista que extrae, normaliza, bandea (catálogo 5.2) y expande
con protección SSRF las URLs de un correo. Sin wiring al pipeline (research
D11): lo consumen las specs 006/007/008.

API pública:
- `analizar_urls(email_data, config=None, deps=None) -> ResultadoURLs`
- `ConfigURLs` / `ConfiguracionError` (configuración inyectable, D8)
- `DependenciasURLs` / `dependencias_por_defecto` (E/S inyectable, D4–D7/D15)
- Modelos de salida: `ResultadoURLs`, `UrlAnalizada`, `ResultadoExpansion`,
  `BanderaURL`, `EstadisticasURLs` + catálogo `CATALOGO_URL` (I5)
"""

from __future__ import annotations

from src.level2_agent.analisis_urls.configuracion import ConfiguracionError, ConfigURLs
from src.level2_agent.analisis_urls.modelos import (
    CATALOGO_URL,
    DIAS_DOMINIO_NUEVO,
    REDES_PROHIBIDAS,
    TIMEOUT_URL_SEGUNDOS,
    TOPE_SALTOS,
    UMBRAL_URL_LARGA,
    BanderaURL,
    EstadisticasURLs,
    ResultadoExpansion,
    ResultadoURLs,
    UrlAnalizada,
)
from src.level2_agent.analisis_urls.motor import analizar_urls
from src.level2_agent.analisis_urls.puertos import (
    CacheVacia,
    ClienteHTTPRequests,
    DependenciasURLs,
    ResolvedorDNSGetaddrinfo,
    RespuestaRedireccion,
    SinRDAP,
    dependencias_por_defecto,
)

__all__ = [
    "CATALOGO_URL",
    "DIAS_DOMINIO_NUEVO",
    "REDES_PROHIBIDAS",
    "TIMEOUT_URL_SEGUNDOS",
    "TOPE_SALTOS",
    "UMBRAL_URL_LARGA",
    "BanderaURL",
    "CacheVacia",
    "ClienteHTTPRequests",
    "ConfiguracionError",
    "ConfigURLs",
    "DependenciasURLs",
    "EstadisticasURLs",
    "ResolvedorDNSGetaddrinfo",
    "RespuestaRedireccion",
    "ResultadoExpansion",
    "ResultadoURLs",
    "SinRDAP",
    "UrlAnalizada",
    "analizar_urls",
    "dependencias_por_defecto",
]
