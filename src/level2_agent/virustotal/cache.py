"""Repositorios de caché y contador diario (spec 006, FR-005/FR-002, research D3).

`CacheMemoria`/`ContadorMemoria` son la implementación en proceso (dobles de
pruebas y respaldo si falta MongoDB); `CacheMongo`/`ContadorMongo` persisten
en `phishguard.vt_cache` / `phishguard.vt_contador`. Si falta
`MONGODB_ATLAS_CLUSTER_URI` o MongoDB no responde se cae a memoria con un
warning: el análisis nunca se rompe (Art. III.9). El índice TTL
(`expira_en`, `expireAfterSeconds=0`) está [VERIFICAR] en quickstart V1.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Final

import pymongo
import pymongo.errors
from src.level2_agent.virustotal.modelos import (
    TTL_ARCHIVO_DIAS,
    TTL_DESCONOCIDO_HORAS,
    TTL_URL_DIAS,
    EntradaCache,
    LastAnalysisStats,
)

logger = logging.getLogger(__name__)

_TTL_DESCONOCIDO = timedelta(hours=TTL_DESCONOCIDO_HORAS)
_TTL_URL = timedelta(days=TTL_URL_DIAS)
_TTL_ARCHIVO = timedelta(days=TTL_ARCHIVO_DIAS)
_TIPOS: Final[frozenset[str]] = frozenset({"archivo", "url", "dominio", "ip"})


def clave_cache(tipo: str, identificador: str) -> str:
    """Clave `'{tipo}:{identificador}'` de `vt_cache` (data-model.md)."""
    return f"{tipo}:{identificador}"


def ttl_para(tipo: str, *, es_desconocido: bool = False) -> timedelta:
    """TTL literal por tipo (FR-005): archivo 7 d; URL/dominio/IP 24 h; desconocido 1 h."""
    if es_desconocido:
        return _TTL_DESCONOCIDO
    if tipo == "archivo":
        return _TTL_ARCHIVO
    if tipo in _TIPOS:
        return _TTL_URL
    raise ValueError(f"tipo de indicador desconocido para la caché: {tipo!r}")


class CacheMemoria:
    """Caché en proceso sobre un dict compartible entre «reinicios» (FR-005)."""

    def __init__(self, almacen: dict[str, EntradaCache] | None = None) -> None:
        self._almacen: dict[str, EntradaCache] = {} if almacen is None else almacen

    def obtener(self, clave: str, ahora: datetime) -> EntradaCache | None:
        """Entrada vigente (`expira_en > ahora`); None si no existe o venció."""
        entrada = self._almacen.get(clave)
        if entrada is None or entrada.expira_en <= ahora:
            return None
        return entrada

    def guardar(self, entrada: EntradaCache) -> None:
        """Guarda o reemplaza la entrada por su clave."""
        self._almacen[entrada.clave] = entrada

    def limpiar(self) -> None:
        """Vacía la caché (solo para pruebas que simulan un proceso nuevo)."""
        self._almacen.clear()


class CacheMongo:
    """Adapter pymongo sobre `phishguard.vt_cache` con índice TTL [VERIFICAR] (D3)."""

    def __init__(self, uri: str | None = None) -> None:
        self._respaldo = CacheMemoria()
        self._coleccion: Any | None = None
        efectiva = (
            uri if uri is not None else os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "").strip()
        )
        if not efectiva:
            logger.warning(
                "MONGODB_ATLAS_CLUSTER_URI ausente: vt_cache en memoria (no persiste reinicios)"
            )
            return
        try:
            cliente: Any = pymongo.MongoClient(efectiva, serverSelectionTimeoutMS=5000)
            coleccion = cliente["phishguard"]["vt_cache"]
            coleccion.create_index("expira_en", expireAfterSeconds=0)
            self._coleccion = coleccion
        except Exception as exc:  # MongoDB caído no debe romper el análisis (III.9)
            logger.warning("MongoDB no disponible para vt_cache: usando memoria (%s)", exc)

    def obtener(self, clave: str, ahora: datetime) -> EntradaCache | None:
        """Documento vigente de `vt_cache` o respaldo en memoria (III.9)."""
        if self._coleccion is None:
            return self._respaldo.obtener(clave, ahora)
        documento = self._coleccion.find_one({"_id": clave, "expira_en": {"$gt": ahora}})
        if documento is None:
            return None
        return _entrada_desde_documento(documento)

    def guardar(self, entrada: EntradaCache) -> None:
        """Upsert del documento con `expira_en` indexado por TTL (FR-005)."""
        if self._coleccion is None:
            self._respaldo.guardar(entrada)
            return
        self._coleccion.update_one(
            {"_id": entrada.clave},
            {"$set": _documento_desde_entrada(entrada)},
            upsert=True,
        )


def _documento_desde_entrada(entrada: EntradaCache) -> dict[str, Any]:
    """Entrada → documento de MongoDB (stats serializados o None)."""
    return {
        "clasificacion": entrada.clasificacion,
        "stats": entrada.stats.model_dump() if entrada.stats is not None else None,
        "guardada_en": entrada.guardada_en,
        "expira_en": entrada.expira_en,
    }


def _entrada_desde_documento(documento: dict[str, Any]) -> EntradaCache:
    """Documento de MongoDB → EntradaCache (stats ausentes → None)."""
    crudos = documento.get("stats")
    stats = LastAnalysisStats(**crudos) if isinstance(crudos, dict) else None
    return EntradaCache(
        clave=str(documento["_id"]),
        clasificacion=documento["clasificacion"],
        stats=stats,
        guardada_en=documento["guardada_en"],
        expira_en=documento["expira_en"],
    )


class ContadorMemoria:
    """Contador diario en proceso con tope (FR-002); `almacen` compartible (reinicio)."""

    def __init__(self, tope: int, almacen: dict[str, int] | None = None) -> None:
        self._tope = tope
        self._almacen: dict[str, int] = {} if almacen is None else almacen

    def consumir(self, dia: str) -> bool:
        """Suma 1 uso si queda cuota del día; False si ya se agotó (D5b)."""
        usos = self._almacen.get(dia, 0)
        if self._tope > 0 and usos >= self._tope:
            return False
        self._almacen[dia] = usos + 1
        return True

    def usos(self, dia: str) -> int:
        """Usos registrados del día (0 si el día no existe)."""
        return self._almacen.get(dia, 0)


class ContadorMongo:
    """Contador diario persistente en `phishguard.vt_contador` (FR-002, D3).

    `tope=0` ⇒ sin tope. Si falta la URI o MongoDB no responde se cae a
    memoria con warning (Art. III.9): el tope no sobreviviría reinicios.
    """

    def __init__(self, tope: int, uri: str | None = None) -> None:
        self._tope = tope
        self._respaldo = ContadorMemoria(tope=tope)
        self._coleccion: Any | None = None
        efectiva = (
            uri if uri is not None else os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "").strip()
        )
        if not efectiva:
            logger.warning(
                "MONGODB_ATLAS_CLUSTER_URI ausente: vt_contador en memoria (no persiste reinicios)"
            )
            return
        try:
            cliente: Any = pymongo.MongoClient(efectiva, serverSelectionTimeoutMS=5000)
            self._coleccion = cliente["phishguard"]["vt_contador"]
        except Exception as exc:
            logger.warning("MongoDB no disponible para vt_contador: usando memoria (%s)", exc)

    def consumir(self, dia: str) -> bool:
        """Incrementa el día si queda cuota; False si ya está en el tope (FR-002)."""
        if self._coleccion is None:
            return self._respaldo.consumir(dia)
        try:
            if self._tope <= 0:
                self._coleccion.update_one({"_id": dia}, {"$inc": {"usos": 1}}, upsert=True)
                return True
            encontrado = self._coleccion.find_one_and_update(
                {"_id": dia, "usos": {"$lt": self._tope}}, {"$inc": {"usos": 1}}
            )
            if encontrado is not None:
                return True
            try:
                self._coleccion.insert_one({"_id": dia, "usos": 1})
                return True
            except pymongo.errors.DuplicateKeyError:
                return False  # ya está en el tope (otro proceso llegó primero)
        except Exception as exc:
            logger.warning("MongoDB falló en vt_contador: usando memoria (%s)", exc)
            return self._respaldo.consumir(dia)

    def usos(self, dia: str) -> int:
        """Usos del día en Mongo o en el respaldo en memoria (III.9)."""
        if self._coleccion is None:
            return self._respaldo.usos(dia)
        try:
            documento = self._coleccion.find_one({"_id": dia})
            return int(documento.get("usos", 0)) if documento else 0
        except Exception as exc:
            logger.warning("MongoDB falló en vt_contador: usando memoria (%s)", exc)
            return self._respaldo.usos(dia)
