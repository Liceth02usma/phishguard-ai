"""Doble de cliente MongoDB para las pruebas de migración (Art. II.5 — sin red).

Implementa SOLO la interfaz que consume ``scripts/eliminar_memoria.py`` sobre una
estructura ``{base: {coleccion: [docs]}}`` observable por las pruebas. Nunca
habla con MongoDB Atlas real.

Ver ``specs/001-eliminar-memoria/data-model.md`` §4.1.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast


class FakeCursor:
    """Cursor mínimo con ``sort`` y ``limit`` (interfaz de pymongo)."""

    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = list(docs)

    def sort(self, campo: str, orden: int = 1) -> FakeCursor:
        """Ordena por ``campo`` (1 ascendente, -1 descendente)."""
        self._docs.sort(key=cast(Any, lambda d: d.get(campo)), reverse=orden < 0)
        return self

    def limit(self, n: int) -> FakeCursor:
        """Limita el cursor a ``n`` documentos."""
        self._docs = self._docs[:n]
        return self

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._docs)


class FakeColeccion:
    """Colección en memoria con la superficie usada por el script."""

    def __init__(self, nombre: str, docs: list[dict[str, Any]], base: FakeBase) -> None:
        self.name = nombre
        self._docs = docs
        self._base = base

    def count_documents(self, filtro: dict[str, Any]) -> int:
        """Cuenta documentos (el filtro ``{}`` lo único soportado)."""
        if filtro:
            raise NotImplementedError(f"filtro no soportado por el doble: {filtro}")
        return len(self._docs)

    def find(
        self, filtro: dict[str, Any], proyeccion: dict[str, Any] | None = None
    ) -> FakeCursor:
        """Devuelve un cursor sobre los documentos (sin filtro, como usa el script)."""
        if filtro:
            raise NotImplementedError(f"filtro no soportado por el doble: {filtro}")
        return FakeCursor([dict(d) for d in self._docs])

    def delete_many(self, filtro: dict[str, Any]) -> SimpleNamespace:
        """Elimina por ``{"_id": {"$in": [...]}}`` y devuelve ``deleted_count``."""
        ids = filtro.get("_id", {}).get("$in")
        if ids is None:
            borrados = len(self._docs)
            self._docs.clear()
        else:
            objetivo = set(ids)
            conservados = [d for d in self._docs if d.get("_id") not in objetivo]
            borrados = len(self._docs) - len(conservados)
            self._docs = conservados
        return SimpleNamespace(deleted_count=borrados)

    def drop(self) -> None:
        """Elimina la colección de la base (ya no debe existir)."""
        self._base.eliminar_coleccion(self.name)

    @property
    def documentos(self) -> list[dict[str, Any]]:
        """Estado observable de los documentos (para aserciones de prueba)."""
        return self._docs


class FakeBase:
    """Base en memoria con ``list_collection_names`` y ``get_collection``."""

    def __init__(self, nombre: str, colecciones: dict[str, list[dict[str, Any]]]) -> None:
        self.name = nombre
        self._colecciones = colecciones

    def list_collection_names(self) -> list[str]:
        """Nombre de las colecciones existentes (instantánea, segura para iterar)."""
        return list(self._colecciones)

    def get_collection(self, nombre: str) -> FakeColeccion:
        """Devuelve la colección; si no existe, la crea vacía (como pymongo)."""
        if nombre not in self._colecciones:
            self._colecciones[nombre] = []
        return FakeColeccion(nombre, self._colecciones[nombre], self)

    def eliminar_coleccion(self, nombre: str) -> None:
        """Quita la colección de la estructura (la usa ``FakeColeccion.drop``)."""
        self._colecciones.pop(nombre, None)

    @property
    def colecciones(self) -> dict[str, list[dict[str, Any]]]:
        """Estado observable de las colecciones (para aserciones de prueba)."""
        return self._colecciones


class FakeClienteMongo:
    """Cliente mínimo: ``get_database(nombre)``; bases inexistentes = vacías."""

    def __init__(self, bases: dict[str, dict[str, list[dict[str, Any]]]]) -> None:
        self._bases = {nombre: dict(cols) for nombre, cols in bases.items()}
        self.bases: dict[str, dict[str, list[dict[str, Any]]]] = self._bases

    def get_database(self, nombre: str) -> FakeBase:
        """Base existente o vacía (pymongo no falla: es perezoso)."""
        return FakeBase(nombre, self._bases.setdefault(nombre, {}))

    def close(self) -> None:
        """Cierra el cliente (no-op en el doble)."""
