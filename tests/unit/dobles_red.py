"""Dobles de red para las pruebas de la spec 004 (Art. II.5 — cero red externa).

Incluye un reloj falso avanzable (D15), un resolvedor DNS con mapping
host→IPs, un cliente HTTP con respuestas guionizadas, un cliente real sobre
`http.client` que conecta SIEMPRE al servidor local de prueba (para que la
validación SSRF corra sobre IPs "públicas" falsas mientras la conexión real
es a loopback) y el servidor local de loopback con contadores de peticiones
y de escrituras de cuerpo (AC-URL-02/04).
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address, IPv6Address, ip_address
from urllib.parse import urlsplit

from src.level2_agent.analisis_urls.puertos import (
    CacheReputacionURL,
    CacheVacia,
    ClienteHTTPExpansion,
    ClienteRDAP,
    DependenciasURLs,
    Reloj,
    ResolvedorDNS,
    RespuestaRedireccion,
    SinRDAP,
)

__all__ = [
    "ClienteHTTPDouble",
    "ClienteHTTPServidorLocal",
    "DependenciasURLs",
    "RelojFalso",
    "ResolvedorDNSDouble",
    "RespuestaRedireccion",
    "ServidorLocal",
    "deps_de_prueba",
    "servidor_local",
]


class RelojFalso:
    """Reloj monotónico avanzable (D15): sin tiempo real en pruebas."""

    def __init__(self, inicial: float = 0.0) -> None:
        self._momento = inicial

    def __call__(self) -> float:
        """Devuelve el momento actual (segundos ficticios)."""
        return self._momento

    def avanzar(self, segundos: float) -> None:
        """Avanza el reloj manualmente."""
        self._momento += segundos


class ResolvedorDNSDouble:
    """Resolvedor DNS con mapping host→IPs; host desconocido simula fallo DNS."""

    def __init__(self, mapping: dict[str, list[str]] | None = None) -> None:
        self._mapping = dict(mapping or {})
        self.consultas: list[str] = []

    def agregar(self, host: str, *ips: str) -> None:
        """Registra la resolución de un host."""
        self._mapping[host] = list(ips)

    def resolver(self, host: str) -> list[IPv4Address | IPv6Address]:
        """Devuelve las IPs del host; si no está en el mapping lanza OSError."""
        self.consultas.append(host)
        if host not in self._mapping:
            raise OSError(f"nombre no resoluble: {host}")
        return [ip_address(ip) for ip in self._mapping[host]]


RespuestaGuionizada = RespuestaRedireccion | Callable[[str], RespuestaRedireccion]


class ClienteHTTPDouble:
    """Cliente HTTP con respuestas guionizadas; registra cada petición recibida."""

    def __init__(self, respuestas: Sequence[RespuestaGuionizada] | None = None) -> None:
        self._respuestas: list[RespuestaGuionizada] = list(respuestas or [])
        self.peticiones: list[str] = []

    def solicitar(self, url: str) -> RespuestaRedireccion:
        """Devuelve la siguiente respuesta guionizada; sin guion lanza OSError."""
        self.peticiones.append(url)
        if not self._respuestas:
            raise OSError("sin respuesta guionizada")
        elemento = self._respuestas.pop(0)
        return elemento(url) if callable(elemento) else elemento


class ClienteHTTPServidorLocal:
    """Cliente HTTP real (http.client) conectado al servidor local de prueba.

    Conecta SIEMPRE a `host_local:puerto` (loopback) sin importar el host de
    la URL, para que la validación SSRF se ejerza de verdad sobre las IPs
    resueltas mientras la conexión física es local. Solo usa HEAD y nunca
    descarga cuerpos (AC-URL-04 / I2).
    """

    def __init__(self, host_local: str = "127.0.0.1", puerto: int = 80) -> None:
        self._host = host_local
        self._puerto = puerto
        self.peticiones: list[str] = []
        self.cuerpos_leidos = 0

    def solicitar(self, url: str) -> RespuestaRedireccion:
        """HEAD contra el servidor local; lee solo cabeceras, jamás el cuerpo."""
        partes = urlsplit(url)
        ruta = partes.path or "/"
        if partes.query:
            ruta = f"{ruta}?{partes.query}"
        self.peticiones.append(url)
        conexion = HTTPConnection(self._host, self._puerto, timeout=5)
        try:
            conexion.request("HEAD", ruta, headers={"Host": partes.netloc})
            respuesta = conexion.getresponse()
            location = respuesta.getheader("Location")
            return RespuestaRedireccion(
                status=respuesta.status, location=location, ya_leido=False
            )
        finally:
            conexion.close()


class ServidorLocal:
    """Servidor HTTP de loopback con rutas guionizadas y contadores."""

    def __init__(self, rutas: Mapping[str, tuple[int, str | None]]) -> None:
        self.rutas = dict(rutas)
        self.peticiones: list[str] = []
        self.escrituras_cuerpo = 0
        self.puerto = 0
        self._servidor: ThreadingHTTPServer | None = None
        self._hilo: threading.Thread | None = None

    def arrancar(self) -> None:
        """Arranca el servidor en 127.0.0.1 y un puerto efímero."""
        servidor_ref = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, formato: str, *args: object) -> None:
                """Silencioso: los logs de la prueba no van a stderr."""
                return

            def _atender(self, metodo: str) -> None:
                servidor_ref.peticiones.append(f"{metodo} {self.path}")
                status, location = servidor_ref.rutas.get(self.path, (404, None))
                self.send_response(status)
                if location is not None:
                    self.send_header("Location", location)
                self.send_header("Content-Length", "1024")
                self.end_headers()
                if metodo == "GET":
                    servidor_ref.escrituras_cuerpo += 1
                    # El cliente cerró sin leer: era esperado (AC-URL-04).
                    with suppress(OSError):
                        self.wfile.write(b"x" * 1024)

            def do_HEAD(self) -> None:
                """Responde solo cabeceras (método de la expansión, FR-003)."""
                self._atender("HEAD")

            def do_GET(self) -> None:
                """Responde con cuerpo (fallback del adapter, nunca leído)."""
                self._atender("GET")

        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.puerto = self._servidor.server_address[1]
        self._hilo = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        """Detiene el servidor y espera al hilo."""
        if self._servidor is not None:
            self._servidor.shutdown()
            self._servidor.server_close()
        if self._hilo is not None:
            self._hilo.join(timeout=5)


@contextmanager
def servidor_local(rutas: Mapping[str, tuple[int, str | None]]) -> Iterator[ServidorLocal]:
    """Context manager: servidor local arrancado y detenido en todos los caminos."""
    servidor = ServidorLocal(rutas)
    servidor.arrancar()
    try:
        yield servidor
    finally:
        servidor.detener()


def deps_de_prueba(
    *,
    resolvedor: ResolvedorDNS | None = None,
    http: ClienteHTTPExpansion | None = None,
    cache: CacheReputacionURL | None = None,
    rdap: ClienteRDAP | None = None,
    reloj: Reloj | None = None,
) -> DependenciasURLs:
    """Dependencias 100 % dobles para pruebas sin red (Art. II.5)."""
    return DependenciasURLs(
        resolvedor=resolvedor if resolvedor is not None else ResolvedorDNSDouble(),
        http=http if http is not None else ClienteHTTPDouble(),
        cache=cache if cache is not None else CacheVacia(),
        rdap=rdap if rdap is not None else SinRDAP(),
        reloj=reloj if reloj is not None else RelojFalso(),
    )
