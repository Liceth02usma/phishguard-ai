"""Dobles de prueba del cliente VirusTotal (spec 006, research D2/D11, Art. II.5).

Cero red real: `httpx.MockTransport` con respuestas dictadas o leídas de
`respuestas_vt/*.json` (D12), reloj avanzable, dormir que captura esperas,
jitter fijo y caché/contador en memoria compartibles entre «procesos».
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from src.level2_agent.virustotal.puertos import ClienteHttpx, DependenciasVT

BASE_PRUEBA = "https://www.virustotal.com/api/v3"
"""Base que httpx pone delante de cada path registrado (M06.2)."""

RESPUESTAS_DIR = Path(__file__).parent / "respuestas_vt"
"""Respuestas grabadas y anonimizadas (D12; NUNCA tests/fixtures/)."""


def cargar_respuesta(nombre: str) -> dict[str, Any]:
    """Carga una respuesta VT grabada y anonimizada (D12)."""
    return json.loads((RESPUESTAS_DIR / nombre).read_text(encoding="utf-8"))


class RelojFalso:
    """Reloj UTC avanzable: `avanzar(segundos)` para valores límite (II.5)."""

    def __init__(self, inicio: datetime | None = None) -> None:
        self._ahora = inicio or datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self._ahora

    def avanzar(self, segundos: float) -> None:
        """Mueve el reloj la cantidad de segundos indicada."""
        self._ahora += timedelta(seconds=segundos)


class DormirFalso:
    """Captura las esperas solicitadas y avanza el reloj (cero espera real)."""

    def __init__(self, reloj: RelojFalso | None = None) -> None:
        self.esperas: list[float] = []
        self._reloj = reloj

    async def __call__(self, segundos: float) -> None:
        self.esperas.append(segundos)
        if self._reloj is not None:
            self._reloj.avanzar(segundos)


def jitter_cero() -> float:
    """Jitter fijo 0.0 para esperas exponenciales deterministas (D6)."""
    return 0.0


@dataclass
class RespuestaDoble:
    """Respuesta que el doble devolverá: estado, cuerpo JSON y cabeceras."""

    status: int = 200
    json_body: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


@dataclass
class PeticionRegistrada:
    """Petición que llegó al doble (para afirmar «sin llamada» o «cero POST»)."""

    metodo: str
    path: str
    query: str
    cuerpo: bytes = b""


@dataclass
class ClienteDoble:
    """Cliente HTTP VT de prueba sobre `httpx.MockTransport` (D2, G11).

    Sirve secuencias de respuestas registradas por `(metodo, path)`; la
    última respuesta de una secuencia se repite. Cualquier petición NO
    registrada lanza `AssertionError` y falla la prueba (G11). Todo llega a
    través del adapter real `ClienteHttpx`, así que también se prueba a él.
    """

    rutas: dict[tuple[str, str], list[RespuestaDoble]] = field(default_factory=dict)
    peticiones: list[PeticionRegistrada] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._rutas = {k: list(v) for k, v in self.rutas.items()}
        transporte = httpx.MockTransport(self._manejador)
        self._http = httpx.AsyncClient(transport=transporte)
        self.adaptador = ClienteHttpx(api_key="clave-de-prueba", transporte=self._http)

    def registrar(self, metodo: str, path: str, *respuestas: RespuestaDoble) -> None:
        """Registra una secuencia de respuestas para (metodo, path)."""
        self._rutas[(metodo.upper(), path)] = list(respuestas)

    def contar(self, metodo: str, path: str) -> int:
        """Cuenta peticiones registradas que coinciden con (metodo, path)."""
        return sum(1 for p in self.peticiones if p.metodo == metodo.upper() and p.path == path)

    def _manejador(self, solicitud: httpx.Request) -> httpx.Response:
        """Devuelve la respuesta dictada o falla si la petición no existe."""
        metodo = solicitud.method.upper()
        path = solicitud.url.path
        if path.startswith("/api/v3"):
            path = path[len("/api/v3") :]
        self.peticiones.append(
            PeticionRegistrada(
                metodo=metodo,
                path=path,
                query=solicitud.url.query,
                cuerpo=solicitud.content,
            )
        )
        cola = self._rutas.get((metodo, path))
        if not cola:
            raise AssertionError(f"petición NO registrada en el doble: {metodo} {path}")
        especificacion = cola.pop(0) if len(cola) > 1 else cola[0]
        return httpx.Response(
            status_code=especificacion.status,
            json=especificacion.json_body,
            headers=especificacion.headers,
        )


def deps_prueba(
    cliente: ClienteDoble,
    *,
    cache: Any = None,
    contador: Any = None,
    reloj: RelojFalso | None = None,
    dormir: DormirFalso | None = None,
) -> DependenciasVT:
    """Arma `DependenciasVT` con dobles deterministas (Art. II.5).

    Por defecto usa caché/contador en memoria del paquete `virustotal` y
    jitter fijo 0.0; todo sobreescribible por prueba.
    """
    from src.level2_agent.virustotal.cache import CacheMemoria, ContadorMemoria

    reloj_efectivo = reloj if reloj is not None else RelojFalso()
    dormir_efectivo = dormir if dormir is not None else DormirFalso(reloj_efectivo)
    return DependenciasVT(
        cliente=cliente.adaptador,
        cache=cache if cache is not None else CacheMemoria(),
        contador=contador if contador is not None else ContadorMemoria(tope=0),
        reloj=reloj_efectivo,
        dormir=dormir_efectivo,
        jitter=jitter_cero,
    )
