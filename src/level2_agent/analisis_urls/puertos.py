"""Puertos (interfaces) del análisis de URLs y sus defaults de producción (spec 004).

Adapters inyectables para determinismo (Art. II.5): DNS, cliente HTTP de
expansión, caché de reputación de VT (D4), RDAP (D5) y reloj (D15). Las
pruebas sustituyen todos estos por dobles (`tests/unit/dobles_red.py`).
"""

from __future__ import annotations

import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Protocol, runtime_checkable

import requests

from src.level2_agent.analisis_urls.modelos import TIMEOUT_URL_SEGUNDOS

Reloj = Callable[[], float]
"""Reloj monotónico inyectable: producción usa `time.monotonic` (D15)."""


@runtime_checkable
class ResolvedorDNS(Protocol):
    """Resuelve un host a sus IPs; el validador SSRF exige que TODAS pasen (D7)."""

    def resolver(self, host: str) -> list[IPv4Address | IPv6Address]:
        """Devuelve las IPs resueltas; puede lanzar `OSError` (→ error_controlado)."""
        ...


@dataclass(frozen=True)
class RespuestaRedireccion:
    """Respuesta sin cuerpo: la expansión solo mira status y Location (FR-005)."""

    status: int
    location: str | None
    ya_leido: bool = False
    """Debe ser siempre False: nadie descarga el cuerpo (AC-URL-04, I2)."""


@runtime_checkable
class ClienteHTTPExpansion(Protocol):
    """Cliente de expansión sin auto-redirección (cada salto se valida, D6/D7)."""

    def solicitar(self, url: str) -> RespuestaRedireccion:
        """HEAD (o GET sin cuerpo); puede lanzar excepciones de red (→ error_controlado)."""
        ...


@runtime_checkable
class CacheReputacionURL(Protocol):
    """Caché de reputación de VirusTotal (FR-006)."""

    def conoce(self, url_saneada: str) -> bool:
        """True si la reputación ya es conocida → no expandir por conexión directa."""
        ...


@runtime_checkable
class ClienteRDAP(Protocol):
    """Antigüedad de dominio vía RDAP para `URL_DOMINIO_NUEVO` (D5)."""

    def antiguedad_dias(self, dominio: str) -> int | None:
        """Edad en días, o None si se desconoce (desconocido ≠ nuevo, V.1)."""
        ...


class CacheVacia:
    """Caché por defecto: nada conocido → se expande (research D4)."""

    def conoce(self, url_saneada: str) -> bool:
        """Siempre False: sin caché de VT la expansión procede (protegida por SSRF)."""
        return False


class SinRDAP:
    """RDAP por defecto: edad desconocida → la bandera nunca se activa (D5)."""

    def antiguedad_dias(self, dominio: str) -> int | None:
        """Siempre None: sin cliente RDAP no se emite `URL_DOMINIO_NUEVO`."""
        return None


class ResolvedorDNSGetaddrinfo:
    """Resolución de producción con `socket.getaddrinfo` (stdlib, sin dependencias)."""

    def resolver(self, host: str) -> list[IPv4Address | IPv6Address]:
        """Resuelve el host y devuelve sus IPs únicas; propaga `OSError`."""
        salida: list[IPv4Address | IPv6Address] = []
        for info in socket.getaddrinfo(host, None):
            ip = ip_address(info[4][0])
            if ip not in salida:
                salida.append(ip)
        return salida


class ClienteHTTPRequests:
    """Adapter de producción con `requests` (research D6).

    Sin auto-redirección (cada salto lo valida el motor), `HEAD` con
    fallback `GET` en 403/405/501, `stream=True` y cierre sin leer el
    cuerpo (FR-005, AC-URL-04 / I2).
    """

    def __init__(self, timeout: float = TIMEOUT_URL_SEGUNDOS) -> None:
        self._timeout = timeout

    def solicitar(self, url: str) -> RespuestaRedireccion:
        """Petición de cabeceras a la URL; nunca lee el cuerpo de la respuesta."""
        respuesta = requests.head(
            url, allow_redirects=False, stream=True, timeout=self._timeout
        )
        try:
            if respuesta.status_code in (403, 405, 501):
                respuesta.close()
                respuesta = requests.get(
                    url,
                    allow_redirects=False,
                    stream=True,
                    timeout=self._timeout,
                    headers={"Range": "bytes=0-0"},
                )
            location = respuesta.headers.get("Location")
            return RespuestaRedireccion(
                status=respuesta.status_code, location=location, ya_leido=False
            )
        finally:
            respuesta.close()


@dataclass(frozen=True)
class DependenciasURLs:
    """E/S inyectada del análisis de URLs (3er parámetro de `analizar_urls`, D4–D7/D15)."""

    resolvedor: ResolvedorDNS
    http: ClienteHTTPExpansion
    cache: CacheReputacionURL
    rdap: ClienteRDAP
    reloj: Reloj


def dependencias_por_defecto() -> DependenciasURLs:
    """Implementaciones de producción: DNS real, `requests`, caché vacía, sin RDAP."""
    return DependenciasURLs(
        resolvedor=ResolvedorDNSGetaddrinfo(),
        http=ClienteHTTPRequests(),
        cache=CacheVacia(),
        rdap=SinRDAP(),
        reloj=time.monotonic,
    )
