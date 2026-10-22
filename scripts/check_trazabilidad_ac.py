"""Compuerta de trazabilidad AC→prueba (RF4, AC-CAL-05).

Lista los criterios de aceptación definidos en una spec que no tienen
ninguna prueba marcada con @pytest.mark.ac.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._comunes import ResultadoCompuerta

PATRON_AC: re.Pattern[str] = re.compile(r"\b(AC-[A-Z]+-\d+)\b")
PATRON_MARKER: re.Pattern[str] = re.compile(
    r'@pytest\.mark\.ac\(\s*["\']([A-Z]+-[A-Z]+-\d+)["\']\s*\)'
)


def extraer_acs_de_spec(texto_spec: str) -> list[str]:
    """Extrae los IDs AC-XXX-NN de una spec, en orden de aparición, sin duplicados."""
    vistos: set[str] = set()
    resultado: list[str] = []
    for match in PATRON_AC.finditer(texto_spec):
        ac_id = match.group(1)
        if ac_id not in vistos:
            vistos.add(ac_id)
            resultado.append(ac_id)
    return resultado


def extraer_acs_de_pruebas(texto_pruebas: str) -> set[str]:
    """Extrae los IDs AC asociados a pruebas vía @pytest.mark.ac."""
    return {match.group(1) for match in PATRON_MARKER.finditer(texto_pruebas)}


def evaluar_trazabilidad(
    acs_spec: list[str],
    acs_pruebas: set[str],
) -> ResultadoCompuerta:
    """Evalúa si todo AC de la spec tiene al menos una prueba marcada.

    Args:
        acs_spec: IDs AC definidos en la spec (orden preservado).
        acs_pruebas: IDs AC cubiertos por pruebas marcadas.

    Returns:
        ResultadoCompuerta con ok=True si todos los AC tienen prueba;
        si no, detalles lista los AC faltantes.
    """
    faltantes = [ac for ac in acs_spec if ac not in acs_pruebas]
    return ResultadoCompuerta(
        nombre="trazabilidad_ac",
        ok=not faltantes,
        detalles=faltantes,
    )


def _leer_pruebas(directorios: list[Path]) -> str:
    """Concatena el texto de todos los .py bajo los directorios de pruebas."""
    partes: list[str] = []
    for d in directorios:
        if d.is_dir():
            for py in d.rglob("*.py"):
                try:
                    partes.append(py.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
    return "\n".join(partes)


def main(ruta_spec: str | None = None) -> int:
    """CLI: evalúa trazabilidad y sale 0/1.

    Args:
        ruta_spec: ruta a la spec.md (argumento --spec). Si None, usa sys.argv.
    """
    if ruta_spec is None:
        args = sys.argv[1:]
        if "--spec" in args:
            ruta_spec = args[args.index("--spec") + 1]
        else:
            print("[FAIL] trazabilidad_ac: falta --spec <ruta>")
            return 1

    base = Path(__file__).resolve().parent.parent
    texto_spec = Path(ruta_spec).read_text(encoding="utf-8", errors="replace")
    acs_spec = extraer_acs_de_spec(texto_spec)
    texto_pruebas = _leer_pruebas([base / "tests"])
    acs_pruebas = extraer_acs_de_pruebas(texto_pruebas)
    resultado = evaluar_trazabilidad(acs_spec, acs_pruebas)

    if resultado.ok:
        print(f"[PASS] {resultado.nombre} ({len(acs_spec)} AC cubiertos)")
        return 0
    print(f"[FAIL] {resultado.nombre} — AC sin prueba:")
    for ac in resultado.detalles:
        print(f"  {ac}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
