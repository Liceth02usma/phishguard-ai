"""Expansión de acortadores con validación SSRF por salto (FR-003..FR-006, D6/D7).

Máquina de estados de data-model.md: `no_acortadora`, `reputacion_conocida`,
`esquema_no_permitido`, `expandida`, `limite_saltos`, `limite_tiempo`,
`bloqueada_ssrf` y `error_controlado`. Cada IP se valida ANTES de conectar;
el destino final nunca se sigue si no está en la lista configurable de
acortadores; jamás se emite más de `tope_saltos` peticiones (I7) ni se lee
el cuerpo (FR-005). El tiempo se mide con el reloj inyectado (D15).
"""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

import requests
from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.modelos import ResultadoExpansion
from src.level2_agent.analisis_urls.puertos import DependenciasURLs
from src.level2_agent.analisis_urls.sanitizacion import sanitizar_parametros
from src.level2_agent.analisis_urls.ssrf import validar_host

_ESQUEMAS_OK = ("http", "https")


def _host_de(url: str) -> str:
    """Host en minúsculas de una URL; irresoluble → cadena vacía."""
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _esquema_de(url: str) -> str:
    """Esquema en minúsculas; irresoluble → cadena vacía."""
    try:
        return urlsplit(url).scheme.lower()
    except ValueError:
        return ""


def _error(saltos: int, duracion_ms: int, motivo: str) -> ResultadoExpansion:
    """Error controlado con motivo acotado y sin PII (III.9, V.4)."""
    return ResultadoExpansion(
        estado="error_controlado", saltos=saltos, duracion_ms=duracion_ms, motivo=motivo[:120]
    )


def expandir_acortador(
    url_saneada: str, config: ConfigURLs, deps: DependenciasURLs
) -> ResultadoExpansion:
    """Expande un acortador validando cada salto; nunca lanza excepción no controlada."""
    t0 = deps.reloj()

    def _ms() -> int:
        return max(0, int((deps.reloj() - t0) * 1000))

    if _esquema_de(url_saneada) not in _ESQUEMAS_OK:
        return ResultadoExpansion(
            estado="esquema_no_permitido", motivo=f"esquema: {_esquema_de(url_saneada)}"
        )
    if _host_de(url_saneada) not in config.acortadores:
        # Solo se expande si el host está en la lista configurable (FR-003).
        return ResultadoExpansion(estado="no_acortadora")
    if deps.cache.conoce(url_saneada):
        # FR-006: reputación conocida ⇒ no hay conexión directa.
        return ResultadoExpansion(estado="reputacion_conocida")

    actual = url_saneada
    saltos = 0
    while True:
        if deps.reloj() - t0 >= config.timeout_url:
            return ResultadoExpansion(estado="limite_tiempo", saltos=saltos, duracion_ms=_ms())

        host = _host_de(actual)
        if not host:
            return _error(saltos, _ms(), "host_irresoluble")
        try:
            permitido, motivo = validar_host(host, deps.resolvedor)
        except OSError as exc:
            return _error(saltos, _ms(), f"dns: {exc}")
        if not permitido:
            return ResultadoExpansion(
                estado="bloqueada_ssrf", saltos=saltos, duracion_ms=_ms(), motivo=motivo
            )

        try:
            respuesta = deps.http.solicitar(actual)
        except (OSError, requests.RequestException) as exc:
            return _error(saltos, _ms(), f"http: {exc}")
        saltos += 1

        if respuesta.status >= 400:
            return _error(saltos, _ms(), f"http_{respuesta.status}")
        if 300 <= respuesta.status < 400:
            if not respuesta.location:
                return _error(saltos, _ms(), "redireccion_sin_location")
            destino = urljoin(actual, respuesta.location)
            if saltos >= config.tope_saltos:
                # Tope alcanzado: SE DETIENE sin seguir el destino (FR-003).
                return ResultadoExpansion(estado="limite_saltos", saltos=saltos, duracion_ms=_ms())
            esquema_destino = _esquema_de(destino)
            if esquema_destino not in _ESQUEMAS_OK:
                return ResultadoExpansion(
                    estado="esquema_no_permitido",
                    saltos=saltos,
                    duracion_ms=_ms(),
                    motivo=f"esquema destino: {esquema_destino}",
                )
            host_destino = _host_de(destino)
            if not host_destino:
                return _error(saltos, _ms(), "host_destino_irresoluble")
            if host_destino in config.acortadores:
                actual = destino
                continue
            # El destino no-acortador: se valida ANTES de declararlo final (FR-004/FR-007).
            try:
                permitido, motivo = validar_host(host_destino, deps.resolvedor)
            except OSError as exc:
                return _error(saltos, _ms(), f"dns: {exc}")
            if not permitido:
                return ResultadoExpansion(
                    estado="bloqueada_ssrf", saltos=saltos, duracion_ms=_ms(), motivo=motivo
                )
            # Seguir está prohibido fuera de la lista: el destino es el final (sanitizado).
            return ResultadoExpansion(
                estado="expandida",
                destino_final=sanitizar_parametros(destino, config),
                saltos=saltos,
                duracion_ms=_ms(),
            )
        return ResultadoExpansion(
            estado="expandida", destino_final=actual, saltos=saltos, duracion_ms=_ms()
        )
