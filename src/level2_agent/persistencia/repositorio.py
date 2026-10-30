"""Repositorio de análisis en MongoDB (spec 011, M14).

RepositorioAnalisis Protocol define la interfaz.
RepositorioReal envuelve pymongo.
RepositorioDoble es un dict in-memory para tests.
RepositorioCacheVT Protocol para caché de VirusTotal.
CacheVTDoble para tests.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from .modelos import (
    COLECCION_ANALISIS,
    COLECCION_FALLIDOS,
    COLECCION_VT_CACHE,
)

logger = logging.getLogger(__name__)


class RepositorioAnalisis(Protocol):
    """Protocol para el repositorio de análisis (D2)."""

    def guardar(self, doc: dict[str, Any]) -> str:
        """Inserta un documento. Retorna el message_id."""
        ...

    def buscar(self, message_id: str) -> dict[str, Any] | None:
        """Busca por message_id. Retorna el documento o None."""
        ...

    def listar(self, filtro: dict[str, Any]) -> list[dict[str, Any]]:
        """Lista documentos que cumplen el filtro."""
        ...

    def borrar(self, message_id: str) -> bool:
        """Elimina por message_id. Retorna True si existía."""
        ...

    def contar(self, filtro: dict[str, Any]) -> int:
        """Cuenta documentos que cumplen el filtro."""
        ...


class RepositorioCacheVT(Protocol):
    """Protocol para la caché de VirusTotal."""

    def borrar_por_message_id(self, message_id: str) -> int:
        """Elimina entradas de caché por message_id. Retorna cuántas."""
        ...


class RepositorioReal:
    """Repositorio real sobre MongoDB.

    Crea índices TTL al inicializar si no existen (FR-003).
    """

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
        self._client: Any = None
        self._db: Any = None

    def _ensure_connection(self) -> Any:
        """Conexión lazy a MongoDB."""
        if self._db is None:
            from pymongo import MongoClient

            self._client = MongoClient(
                self._uri, serverSelectionTimeoutMS=3000
            )
            self._db = self._client["phishguard"]
            self._crear_indices()
        return self._db

    def _crear_indices(self) -> None:
        """Crea índices TTL si no existen (FR-003, AC-PER-02)."""
        db = self._db
        # analyses: TTL 90 días
        db[COLECCION_ANALISIS].create_index(
            "expira_en",
            name="ttl_analisis",
            expireAfterSeconds=0,
        )
        db[COLECCION_ANALISIS].create_index("fecha", name="idx_fecha")
        db[COLECCION_ANALISIS].create_index(
            "veredicto", name="idx_veredicto"
        )
        db[COLECCION_ANALISIS].create_index(
            "message_id", name="idx_message_id", unique=True
        )
        # analyses_fallidos: TTL 30 días
        db[COLECCION_FALLIDOS].create_index(
            "expira_en",
            name="ttl_fallidos",
            expireAfterSeconds=0,
        )
        logger.info("Índices TTL creados/verificados")

    def guardar(self, doc: dict[str, Any]) -> str:
        """Inserta un documento en analyses."""
        db = self._ensure_connection()
        db[COLECCION_ANALISIS].insert_one(doc)
        return str(doc["message_id"])

    def buscar(self, message_id: str) -> dict[str, Any] | None:
        """Busca por message_id."""
        db = self._ensure_connection()
        result = db[COLECCION_ANALISIS].find_one(
            {"message_id": message_id}
        )
        if result:
            result.pop("_id", None)
        return result

    def listar(self, filtro: dict[str, Any]) -> list[dict[str, Any]]:
        """Lista documentos que cumplen el filtro."""
        db = self._ensure_connection()
        docs = list(db[COLECCION_ANALISIS].find(filtro))
        for d in docs:
            d.pop("_id", None)
        return docs

    def borrar(self, message_id: str) -> bool:
        """Elimina por message_id."""
        db = self._ensure_connection()
        result = db[COLECCION_ANALISIS].delete_one(
            {"message_id": message_id}
        )
        return result.deleted_count > 0

    def contar(self, filtro: dict[str, Any]) -> int:
        """Cuenta documentos que cumplen el filtro."""
        db = self._ensure_connection()
        return int(db[COLECCION_ANALISIS].count_documents(filtro))

    def indices_existentes(self) -> list[str]:
        """Retorna nombres de índices existentes."""
        db = self._ensure_connection()
        return list(db[COLECCION_ANALISIS].index_information().keys())


class CacheVTReal:
    """Repositorio real para caché VT sobre MongoDB."""

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
        self._client: Any = None
        self._db: Any = None

    def _ensure_connection(self) -> Any:
        if self._db is None:
            from pymongo import MongoClient

            self._client = MongoClient(
                self._uri, serverSelectionTimeoutMS=3000
            )
            self._db = self._client["phishguard"]
        return self._db

    def borrar_por_message_id(self, message_id: str) -> int:
        """Elimina entradas de caché VT por message_id."""
        db = self._ensure_connection()
        result = db[COLECCION_VT_CACHE].delete_many(
            {"message_id": message_id}
        )
        return int(result.deleted_count)


class RepositorioDoble:
    """Repositorio in-memory para tests."""

    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}

    def guardar(self, doc: dict[str, Any]) -> str:
        msg_id = str(doc["message_id"])
        self._docs[msg_id] = dict(doc)
        return msg_id

    def buscar(self, message_id: str) -> dict[str, Any] | None:
        return self._docs.get(message_id)

    def listar(self, filtro: dict[str, Any]) -> list[dict[str, Any]]:
        """Lista simple: soporta filtros de igualdad directa."""
        results = []
        for doc in self._docs.values():
            match = all(
                doc.get(k) == v for k, v in filtro.items()
            )
            if match:
                results.append(dict(doc))
        return results

    def borrar(self, message_id: str) -> bool:
        if message_id in self._docs:
            del self._docs[message_id]
            return True
        return False

    def contar(self, filtro: dict[str, Any]) -> int:
        return len(self.listar(filtro))

    def indices_existentes(self) -> list[str]:
        return ["ttl_analisis", "idx_fecha", "idx_veredicto", "idx_message_id"]


class CacheVTDoble:
    """Caché VT in-memory para tests."""

    def __init__(self) -> None:
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def agregar(self, message_id: str, entrada: dict[str, Any]) -> None:
        """Agrega entrada de caché para un message_id."""
        if message_id not in self._cache:
            self._cache[message_id] = []
        self._cache[message_id].append(entrada)

    def borrar_por_message_id(self, message_id: str) -> int:
        count = len(self._cache.get(message_id, []))
        self._cache.pop(message_id, None)
        return count
