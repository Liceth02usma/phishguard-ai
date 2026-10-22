"""Compuerta de longitud de archivos (RF2, AC-CAL-01).

Falla si algún .py de src/ o tests/ supera LIMITE_LINEAS (500) líneas.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._comunes import DIRECTORIOS_LONGITUD, LIMITE_LINEAS, ResultadoCompuerta


def _contar_lineas(ruta: Path) -> int:
    """Devuelve el número de líneas de un archivo de texto."""
    with ruta.open("r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def evaluar_longitud(
    paths: Iterable[Path],
    limite: int = LIMITE_LINEAS,
) -> ResultadoCompuerta:
    """Evalúa si todos los archivos cumplen el límite de líneas.

    Args:
        paths: archivos .py a verificar.
        limite: máximo de líneas permitido (default LIMITE_LINEAS=500).

    Returns:
        ResultadoCompuerta con ok=True si todos cumplen; si no, detalles
        lista cada infractor con su cantidad de líneas.
    """
    infractores: list[str] = []
    for ruta in paths:
        try:
            n = _contar_lineas(ruta)
        except OSError as exc:
            infractores.append(f"{ruta}: no se pudo leer ({exc})")
            continue
        if n > limite:
            infractores.append(f"{ruta}: {n} líneas > {limite}")
    return ResultadoCompuerta(
        nombre="longitud_archivos",
        ok=not infractores,
        detalles=infractores,
    )


def _coleccionar_py(directorios: tuple[str, ...]) -> list[Path]:
    """Recolecta todos los .py bajo los directorios dados."""
    base = Path(__file__).resolve().parent.parent
    archivos: list[Path] = []
    for d in directorios:
        raiz = base / d
        if raiz.is_dir():
            archivos.extend(raiz.rglob("*.py"))
    return archivos


def main() -> int:
    """CLI: evalúa src/ y tests/ y sale 0/1."""
    archivos = _coleccionar_py(DIRECTORIOS_LONGITUD)
    resultado = evaluar_longitud(archivos)
    if resultado.ok:
        print(f"[PASS] {resultado.nombre}")
        return 0
    print(f"[FAIL] {resultado.nombre}")
    for d in resultado.detalles:
        print(f"  {d}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
