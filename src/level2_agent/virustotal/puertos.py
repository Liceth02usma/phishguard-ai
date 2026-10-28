"""Puertos e inyección de dependencias del cliente VirusTotal (D2/D3, Art. III.2/III.5).

Define los `Protocol` de sustitución (HTTP, caché, contador, reloj, dormir,
jitter), el adapter `httpx` de producción y el agrupador `DependenciasVT`.
En pruebas se sustituyen por dobles (`tests/unit/dobles_vt.py`) — cero red
real (Art. II.5).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

import httpx
from src.level2_agent.virustotal.modelos import (
    BASE_VT,
    TIMEOUT_CONEXION_SEGUNDOS,
    TIMEOUT_LECTURA_SEGUNDOS,
    EntradaCache,
)

if TYPE_CHECKING:
    from src.level2_agent.virustotal.limitador import Limitador
    from src.level2_agent.virustotal.resiliencia import Cortacircuito


@dataclass(frozen=True)
class RespuestaVT:
    """Respuesta HTTP normalizada del puerto ClienteHTTPVT."""

    status: int
    json: dict[str, Any]
    headers: dict[str, str]


class ClienteHTTPVT(Protocol):
    """Puerto del cliente HTTP asíncrono (M06.3: httpx.AsyncClient)."""

    async def get(self, path: str) -> RespuestaVT:
        """GET contra BASE_VT + path con la cabecera x-apikey."""
        ...

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        content: bytes | None = None,
    ) -> RespuestaVT:
        """POST contra BASE_VT + path (solo tras flags de subida, FR-008)."""
        ...


class RepositorioCacheVT(Protocol):
    """Puerto de la caché de resultados (vt_cache, FR-005)."""

    def obtener(self, clave: str, ahora: datetime) -> EntradaCache | None:
        """Devuelve la entrada vigente o None si no existe/venció."""
        ...

    def guardar(self, entrada: EntradaCache) -> None:
        """Persiste una entrada con su expira_en (índice TTL de Mongo)."""
        ...


class RepositorioContadorVT(Protocol):
    """Puerto del contador diario persistente (vt_contador, FR-002)."""

    def consumir(self, dia: str) -> bool:
        """Intenta consumir 1 uso del día dado; False si ya se agotó."""
        ...

    def usos(self, dia: str) -> int:
        """Usos registrados del día dado (0 si no existe)."""
        ...


class Reloj(Protocol):
    """Reloj inyectable en UTC (Art. II.5: determinismo)."""

    def __call__(self) -> datetime:
        ...


class Dormir(Protocol):
    """Espera inyectable: nunca time.sleep real en pruebas (Art. II.5)."""

    async def __call__(self, segundos: float) -> None:
        ...


class Jitter(Protocol):
    """Aleatoriedad inyectable de los reintentos (M06.3: 'más aleatoriedad')."""

    def __call__(self) -> float:
        ...


def _a_respuesta(respuesta: httpx.Response) -> RespuestaVT:
    """Convierte una httpx.Response en RespuestaVT (cuerpo JSON o vacío)."""
    try:
        datos = respuesta.json()
    except ValueError:
        datos = {}
    claves = {k.lower(): v for k, v in respuesta.headers.items()}
    return RespuestaVT(status=respuesta.status_code, json=datos, headers=claves)


class ClienteHttpx:
    """Adapter de producción: httpx.AsyncClient sobre el puerto ClienteHTTPVT.

    La cabecera `x-apikey` se construye SOLO dentro de la petición y no se
    materializa en variables externas (D10, AC-VT-07).
    """

    def __init__(self, api_key: str, transporte: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._transporte = transporte

    async def get(self, path: str) -> RespuestaVT:
        """GET BASE_VT+path con x-apikey (M06.2)."""
        respuesta = await self._transporte.get(
            f"{BASE_VT}{path}", headers={"x-apikey": self._api_key}
        )
        return _a_respuesta(respuesta)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        content: bytes | None = None,
    ) -> RespuestaVT:
        """POST BASE_VT+path con x-apikey (solo tras flags, FR-008)."""
        respuesta = await self._transporte.post(
            f"{BASE_VT}{path}", headers={"x-apikey": self._api_key}, json=json, content=content
        )
        return _a_respuesta(respuesta)

    async def cerrar(self) -> None:
        """Cierra el subyacente `httpx.AsyncClient` (uso cuando lo crea el cliente)."""
        await self._transporte.aclose()


async def _dormir_real(segundos: float) -> None:
    """Espera real de producción envuelta para satisfacer el puerto `Dormir`."""
    await asyncio.sleep(segundos)


@dataclass(frozen=True)
class DependenciasVT:
    """Grupo de dependencias inyectables del cliente (Art. III.2).

    Los seis puertos sustituibles (§6 del contrato) más los dos objetos de
    estado en proceso — `limitador` (cubeta de minuto) y `cortacircuito` —
    derivados de `reloj`/`dormir` aquí, sin globales de módulo (Art. II.5).
    """

    cliente: ClienteHTTPVT
    cache: RepositorioCacheVT
    contador: RepositorioContadorVT
    reloj: Reloj
    dormir: Dormir
    jitter: Jitter
    limitador: Limitador
    cortacircuito: Cortacircuito


def dependencias_por_defecto() -> DependenciasVT:
    """Dependencias de producción (D2/D3): httpx real, caché y contador

    MongoDB con caída a memoria si falta la URI (Art. III.9), reloj UTC,
    espera real envuelta y jitter aleatorio.
    """
    import random

    from src.level2_agent.virustotal.cache import CacheMongo, ContadorMongo
    from src.level2_agent.virustotal.configuracion import ConfigVT
    from src.level2_agent.virustotal.limitador import Limitador
    from src.level2_agent.virustotal.resiliencia import Cortacircuito

    def reloj() -> datetime:
        return datetime.now(UTC)

    api_key = os.environ.get("VT_API_KEY", "").strip()
    tope_dia = ConfigVT.desde_entorno().tope_dia
    transporte = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=TIMEOUT_CONEXION_SEGUNDOS, read=TIMEOUT_LECTURA_SEGUNDOS
        )
    )
    return DependenciasVT(
        cliente=ClienteHttpx(api_key=api_key, transporte=transporte),
        cache=CacheMongo(),
        contador=ContadorMongo(tope=tope_dia),
        reloj=reloj,
        dormir=_dormir_real,
        jitter=lambda: random.uniform(0.0, 1.0),
        limitador=Limitador(reloj=reloj, dormir=_dormir_real),
        cortacircuito=Cortacircuito(reloj=reloj),
    )
