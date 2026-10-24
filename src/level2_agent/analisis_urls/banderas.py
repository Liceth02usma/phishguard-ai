"""Estrategias de las 13 banderas del catálogo 5.2 (FR-002, Strategy + Registry).

Once evaluadores puros sobre la URL + configuración; `URL_DOMINIO_NUEVO`
necesita la edad (RDAP, se pasa desde el motor) y `REDIRECCION_EXCESIVA`
depende del resultado de la expansión (research D9). Severidad y puntos
jamás se calculan aquí: los copia `modelos.bandera()` del catálogo (I5).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from ipaddress import ip_address
from urllib.parse import parse_qsl, urlsplit

from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.modelos import (
    UMBRAL_URL_LARGA,
    CodigoBandaURL,
    DIAS_DOMINIO_NUEVO,
    ResultadoExpansion,
    UrlAnalizada,
)

# Host mostrado en el texto de un enlace (AC-URL-01: comparar contra el destino).
_HOST_EN_TEXTO = re.compile(r"https?://([A-Za-z0-9.-]+)", re.IGNORECASE)
# Valor con forma de correo en un parámetro (AC-URL-06).
_CORREO_EN_VALOR = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

EvaluadorURL = Callable[[UrlAnalizada, ConfigURLs, ResultadoExpansion | None], bool]

_PUERTOS_ESTANDAR = (80, 443)


def _es_ip(host: str) -> bool:
    try:
        ip_address(host)
    except ValueError:
        return False
    return True


def _texto_distinto_destino(
    url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None
) -> bool:
    """El texto del enlace muestra un host distinto al destino (AC-URL-01)."""
    del config, expansion
    if not url.texto_mostrado:
        return False
    mostrados = _HOST_EN_TEXTO.findall(url.texto_mostrado)
    return any(mostrado.lower() != url.host for mostrado in mostrados)


def _host_ip(url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None) -> bool:
    """El destino es una IP literal (FR-002)."""
    del config, expansion
    return bool(url.host) and _es_ip(url.host)


def _acortada(url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None) -> bool:
    """El host está en la lista configurable de acortadores (FR-003)."""
    del expansion
    return url.host in config.acortadores


def _arroba(url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None) -> bool:
    """`@` en el netloc: engaño de userinfo (`http://banco.com@evil/`, FR-002)."""
    del config, expansion
    try:
        return "@" in urlsplit(url.original).netloc
    except ValueError:
        return False


def _punycode(url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None) -> bool:
    """Host con etiqueta punycode `xn--` (homoglifos, FR-002)."""
    del config, expansion
    return "xn--" in url.host


def _tld_riesgo(url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None) -> bool:
    """TLD en la lista configurable de riesgo (FR-002)."""
    del expansion
    if "." not in url.host:
        return False
    return url.host.rsplit(".", 1)[-1] in config.tlds_riesgo


def _subdominios_excesivos(
    url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None
) -> bool:
    """Más etiquetas de subdominio que el umbral (FR-002; registrable = 2 últimas)."""
    del expansion
    etiquetas = [etiqueta for etiqueta in url.host.split(".") if etiqueta]
    if len(etiquetas) <= 2:
        return False
    return (len(etiquetas) - 2) > config.umbral_subdominios


def _puerto_no_estandar(
    url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None
) -> bool:
    """Puerto explícito distinto de 80/443 (FR-002)."""
    del config, expansion
    try:
        puerto = urlsplit(url.original).port
    except ValueError:
        return False
    return puerto is not None and puerto not in _PUERTOS_ESTANDAR


def _http_sin_cifrado(
    url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None
) -> bool:
    """Esquema `http` sin cifrar (FR-002)."""
    del config, expansion
    return url.esquema == "http"


def _url_larga(url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None) -> bool:
    """URL reportada de más de 200 caracteres (FR-002, límite textual)."""
    del config, expansion
    return len(url.original) > UMBRAL_URL_LARGA


def _parametros_sensibles(
    url: UrlAnalizada, config: ConfigURLs, expansion: ResultadoExpansion | None
) -> bool:
    """Algún parámetro es sensible (los 7 de FR-007) o su valor parece correo."""
    del expansion
    try:
        query = urlsplit(url.original).query
    except ValueError:
        return False
    for clave, valor in parse_qsl(query, keep_blank_values=True):
        if clave.lower() in config.parametros_sensibles or _CORREO_EN_VALOR.match(valor):
            return True
    return False


# Los 11 evaluadores puros, en orden del catálogo (I5). Faltan los dos que
# dependen de contexto externo: URL_DOMINIO_NUEVO (edad RDAP) y
# REDIRECCION_EXCESIVA (estado de la expansión), resueltos en evaluar_banderas_url.
REGISTRO: dict[CodigoBandaURL, EvaluadorURL] = {
    "URL_TEXTO_DISTINTO_DESTINO": _texto_distinto_destino,
    "URL_HOST_IP": _host_ip,
    "URL_ACORTADA": _acortada,
    "URL_ARROBA": _arroba,
    "URL_PUNYCODE": _punycode,
    "URL_TLD_RIESGO": _tld_riesgo,
    "URL_SUBDOMINIOS_EXCESIVOS": _subdominios_excesivos,
    "URL_PUERTO_NO_ESTANDAR": _puerto_no_estandar,
    "URL_HTTP_SIN_CIFRADO": _http_sin_cifrado,
    "URL_LARGA": _url_larga,
    "URL_PARAMETROS_SENSIBLES": _parametros_sensibles,
}


def _bandera_de_expansion(expansion: ResultadoExpansion | None) -> bool:
    """`REDIRECCION_EXCESIVA` solo al cortar por límite de saltos o tiempo (D9)."""
    if expansion is None:
        return False
    return expansion.estado in ("limite_saltos", "limite_tiempo")


def evaluar_banderas_url(
    url: UrlAnalizada,
    config: ConfigURLs,
    expansion: ResultadoExpansion | None = None,
    edad_dominio: int | None = None,
) -> list[CodigoBandaURL]:
    """Devuelve los códigos activados para una URL, en orden del catálogo (I5).

    `edad_dominio` es None cuando RDAP no respondió: desconocido ≠ nuevo (V.1).
    """
    codigos = [codigo for codigo, evaluar in REGISTRO.items() if evaluar(url, config, expansion)]
    if edad_dominio is not None and edad_dominio < DIAS_DOMINIO_NUEVO:
        codigos.append("URL_DOMINIO_NUEVO")
    if _bandera_de_expansion(expansion):
        codigos.append("REDIRECCION_EXCESIVA")
    return codigos
