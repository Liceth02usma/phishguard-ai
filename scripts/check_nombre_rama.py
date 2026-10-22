"""Compuerta de nombre de rama (RF3, AC-CAL-02).

Falla si la rama actual no cumple RAMA_REGEX, excepto main/develop.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._comunes import RAMA_REGEX, RAMAS_EXENTAS, ResultadoCompuerta, rama_actual


def evaluar_nombre_rama(rama: str) -> ResultadoCompuerta:
    """Evalúa si un nombre de rama cumple el patrón (Art. I.2).

    Args:
        rama: nombre de la rama a verificar.

    Returns:
        ResultadoCompuerta con ok=True si la rama es válida o está exenta.
    """
    if rama in RAMAS_EXENTAS:
        return ResultadoCompuerta(nombre="nombre_rama", ok=True)
    if RAMA_REGEX.match(rama):
        return ResultadoCompuerta(nombre="nombre_rama", ok=True)
    return ResultadoCompuerta(
        nombre="nombre_rama",
        ok=False,
        detalles=[f"rama {rama!r} no cumple {RAMA_REGEX.pattern}"],
    )


def main() -> int:
    """CLI: evalúa la rama actual y sale 0/1."""
    try:
        rama = rama_actual()
    except RuntimeError as exc:
        print(f"[FAIL] nombre_rama: {exc}")
        return 1
    resultado = evaluar_nombre_rama(rama)
    if resultado.ok:
        print(f"[PASS] {resultado.nombre} ({rama})")
        return 0
    print(f"[FAIL] {resultado.nombre} ({rama})")
    for d in resultado.detalles:
        print(f"  {d}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
