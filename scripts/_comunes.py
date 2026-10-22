"""Constantes, modelos de datos y helpers compartidos por las compuertas de calidad.

Spec 000-calidad-base. Sin números mágicos (Art. III.6): umbrales y regex
viven aquí como constantes con nombre.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field

# --- Constantes (Art. III.6) ---

LIMITE_LINEAS: int = 500
"""Máximo de líneas por archivo .py (Art. III.1)."""

COBERTURA_MIN: int = 80
"""Umbral mínimo de cobertura de líneas y ramas (Art. II.3)."""

RAMA_REGEX: re.Pattern[str] = re.compile(
    r"^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$"
)
"""Patrón de nombre de rama (Art. I.2)."""

RAMAS_EXENTAS: frozenset[str] = frozenset({"main", "develop"})
"""Ramas exentas de la comprobación de nombre (Art. I.4)."""

DIRECTORIOS_LONGITUD: tuple[str, ...] = ("src", "tests")
"""Directorios revisados por la compuerta de longitud (RF2)."""


# --- Modelos de datos (ver data-model.md) ---


@dataclass(frozen=True)
class Compuerta:
    """Una verificación individual ejecutada por verify.py."""

    nombre: str
    comando: list[str]
    obligatoria: bool = True


@dataclass(frozen=True)
class ResultadoCompuerta:
    """Resultado de ejecutar una Compuerta."""

    nombre: str
    ok: bool
    detalles: list[str] = field(default_factory=list)
    duracion_s: float = 0.0


@dataclass(frozen=True)
class ResultadoVerify:
    """Agregado que devuelve verify.py."""

    resultados: list[ResultadoCompuerta]
    ok: bool
    resumen: str


# --- Helpers ---


def rama_actual() -> str:
    """Devuelve el nombre de la rama git actual.

    Raises:
        RuntimeError: si git no está disponible o no hay rama.
    """
    try:
        resultado = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(f"No se pudo obtener la rama actual: {exc}") from exc
    return resultado.stdout.strip()
