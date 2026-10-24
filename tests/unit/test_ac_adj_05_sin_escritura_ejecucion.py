"""AC-ADJ-05: ningún camino escribe a disco ni ejecuta.

Doble verificación: (a) gate AST sobre src/level2_agent/adjuntos/*.py
prohibiendo open, subprocess, os.startfile, webbrowser, shutil, módulos de
red y escrituras con pathlib (research D12); (b) prueba funcional en tmpdir.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from src.level2_agent.adjuntos import analizar_adjunto

from vector_eicar import generar_eicar

_PAQUETE = Path(__file__).resolve().parents[2] / "src" / "level2_agent" / "adjuntos"

_MODULOS_PROHIBIDOS = frozenset({
    "subprocess", "webbrowser", "shutil", "requests", "urllib", "http", "socket",
})
_METODOS_PROHIBIDOS = frozenset({
    "write_text", "write_bytes", "unlink", "mkdir", "rmdir", "makedirs",
    "startfile", "system", "popen", "exec", "spawn",
})


def _violaciones_ast(ruta: Path) -> list[str]:
    """Escanea un archivo .py y devuelve violaciones del gate de memoria."""
    tree = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    violaciones: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _MODULOS_PROHIBIDOS:
                    violaciones.append(f"import {alias.name} (linea {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in _MODULOS_PROHIBIDOS:
                violaciones.append(f"from {node.module} (linea {node.lineno})")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                violaciones.append(f"open() (linea {node.lineno})")
            elif isinstance(node.func, ast.Attribute) and node.func.attr in _METODOS_PROHIBIDOS:
                violaciones.append(f".{node.func.attr}() (linea {node.lineno})")
    return violaciones


@pytest.mark.ac("AC-ADJ-05")
def test_gate_ast_sin_escritura_ni_ejecucion() -> None:
    """Ningún módulo del paquete adjuntos escribe a disco ni ejecuta."""
    archivos = sorted(_PAQUETE.glob("*.py"))
    assert archivos, "no se encontraron módulos en src/level2_agent/adjuntos/"
    todas: list[str] = []
    for ruta in archivos:
        todas.extend(_violaciones_ast(ruta))
    assert not todas, "violaciones del gate de memoria:\n" + "\n".join(todas)


@pytest.mark.ac("AC-ADJ-05")
def test_funcional_tmpdir_queda_vacio(tmp_path: Path) -> None:
    """Tras analizar todos los fixtures, el directorio temporal queda vacío."""
    payloads = [
        ("doc.pdf", "application/pdf", b"%PDF-1.4\n%%EOF\n"),
        ("data.zip", "application/zip", b"PK\x03\x04" + b"\x00" * 50),
        ("eicar.com", "application/octet-stream", generar_eicar()),
        ("empty.txt", "text/plain", b""),
        ("script.js", "text/javascript", b"alert(1)"),
    ]
    for nombre, tipo, payload in payloads:
        analizar_adjunto(nombre, tipo, payload)
    restantes = list(tmp_path.iterdir())
    assert not restantes, f"se crearon archivos en disco: {restantes}"
