"""Script de una sola ejecución que elimina las colecciones de historial de chat.

FR-003 (spec 001): elimina las colecciones de historial de chat de MongoDB
Atlas DESPUÉS de validar que nada las usa. La base de conocimiento vectorial
(RAG, `phishguard`) nunca se toca (FR-005).

Modo simulación por defecto (Art. V.2); el borrado real requiere la
confirmación explícita `--confirmar`. Contrato completo:
`specs/001-eliminar-memoria/contracts/eliminar-memoria-cli.md`.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

BASE_HISTORIAL = "memory-agent"
COLECCION_HISTORIAL = "memory"
TAMANO_LOTE = 1000
RUTA_MEMORY = Path(__file__).resolve().parents[1] / "src" / "level2_agent" / "memory.py"


def validar_previo() -> str | None:
    """Comprueba que nada usa la memoria antes de borrar (validaciones V1–V3).

    Returns:
        Mensaje de error, o None si todas las validaciones pasan.
    """
    if RUTA_MEMORY.exists():
        return f"{RUTA_MEMORY} aún existe; elimina primero el módulo de memoria (FR-001)"
    if not os.getenv("MONGODB_ATLAS_CLUSTER_URI"):
        return "MONGODB_ATLAS_CLUSTER_URI no está configurada"
    return None


def eliminar_por_lotes(coleccion: Any, tamano_lote: int = TAMANO_LOTE) -> tuple[int, int]:
    """Borra los documentos por lotes de `_id` ascendente sin cargar todo en memoria.

    Args:
        coleccion: colección con la interfaz mínima de pymongo (find/sort/limit/delete_many).
        tamano_lote: tamaño de cada lote (constante `TAMANO_LOTE`).

    Returns:
        Tupla (total de documentos borrados, número de lotes usados).
    """
    total = 0
    lotes = 0
    while True:
        cursor = coleccion.find({}, {"_id": 1}).sort("_id", 1).limit(tamano_lote)
        ids = [doc["_id"] for doc in cursor]
        if not ids:
            return total, lotes
        resultado = coleccion.delete_many({"_id": {"$in": ids}})
        total += int(resultado.deleted_count)
        lotes += 1


def procesar_coleccion(coleccion: Any, confirmar: bool, tamano_lote: int) -> None:
    """Informa (simulación) o elimina (confirmado) una colección de historial."""
    total = int(coleccion.count_documents({}))
    if not confirmar:
        lotes = -(-total // tamano_lote)
        print(
            f"[SIMULACIÓN] {coleccion.name}: {total} documentos en {lotes} lote(s); "
            "no se borra nada."
        )
        return
    borrados, lotes = eliminar_por_lotes(coleccion, tamano_lote)
    coleccion.drop()
    print(
        f"[ELIMINADO] {coleccion.name}: {borrados} documentos en {lotes} lote(s); "
        "colección eliminada."
    )


def eliminar_historial(
    cliente: Any,
    confirmar: bool,
    base: str = BASE_HISTORIAL,
    tamano_lote: int = TAMANO_LOTE,
) -> int:
    """Elimina (o simula) el borrado de TODAS las colecciones de la base de historial.

    Args:
        cliente: cliente MongoDB con la interfaz mínima (get_database).
        confirmar: False = simulación sin escrituras; True = borrado real.
        base: única base admitida; cualquier otra activa la guardia (invariante I1).
        tamano_lote: tamaño de lote para el borrado incremental.

    Returns:
        0 si todo fue bien (incluido "no había colecciones"); 1 si la validación
        o la consulta a MongoDB falló (sin escrituras).
    """
    if base != BASE_HISTORIAL:
        print(
            f"ERROR: la base '{base}' no es el objetivo ('{BASE_HISTORIAL}'); "
            "operación abortada.",
            file=sys.stderr,
        )
        return 1
    try:
        base_datos = cliente.get_database(base)
        nombres = base_datos.list_collection_names()
    except Exception as exc:
        print(f"ERROR: no se pudo consultar MongoDB ({exc}); nada se eliminó.", file=sys.stderr)
        return 1
    if not nombres:
        print(
            f"No hay colecciones de historial en '{base}' "
            f"(esperado: {COLECCION_HISTORIAL}); nada que eliminar."
        )
        return 0
    for nombre in nombres:
        procesar_coleccion(base_datos.get_collection(nombre), confirmar, tamano_lote)
    return 0


def _analizar_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parsea los argumentos del CLI (solo `--confirmar`)."""
    parser = argparse.ArgumentParser(
        description=(
            "Elimina las colecciones de historial de chat de MongoDB "
            f"(base '{BASE_HISTORIAL}'). Por defecto SIMULA; usa --confirmar "
            "para el borrado real. El RAG no se toca."
        )
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="ejecuta el borrado real (sin esta bandera solo se simula)",
    )
    return parser.parse_args(argv)


def _obtener_cliente() -> Any:
    """Crea el cliente pymongo a partir de la variable de entorno (Art. V.3)."""
    from pymongo import MongoClient

    uri = os.environ["MONGODB_ATLAS_CLUSTER_URI"]
    return MongoClient(uri)


def main(argv: Sequence[str] | None = None, cliente: Any = None) -> int:
    """Punto de entrada del CLI (inyección de cliente opcional para pruebas)."""
    args = _analizar_args(argv)
    error = validar_previo()
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if cliente is None:
        cliente = _obtener_cliente()
    return eliminar_historial(cliente, confirmar=args.confirmar)


if __name__ == "__main__":
    sys.exit(main())
