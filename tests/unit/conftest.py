"""Configuración compartida de pytest para las pruebas de las compuertas.

Registra el marker `ac` (Art. II.6) y expone helpers para generar archivos
de prueba temporales.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Registra el marker ac si no está registrado."""
    config.addinivalue_line(
        "markers",
        "ac(id): asocia una prueba a un criterio de aceptación AC-XXX-NN",
    )


@pytest.fixture
def tmp_py_file(tmp_path: Path) -> Iterator[Path]:
    """Factory para crear un archivo .py temporal con N líneas.

    Yields una función `crear(lineas: int, nombre="mod.py") -> Path`.
    """
    def crear(lineas: int, nombre: str = "mod.py") -> Path:
        ruta = tmp_path / nombre
        contenido = "\n".join(f"x = {i}" for i in range(lineas)) + "\n"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    yield crear  # type: ignore[misc]
