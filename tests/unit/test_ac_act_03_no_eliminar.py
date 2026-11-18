"""AC-ACT-03: ninguna ruta de código elimina correos."""

from __future__ import annotations

import ast
import pathlib


def test_accion_enum_no_tiene_eliminar() -> None:
    """El enum Accion no tiene ningún valor de eliminación."""
    from src.level2_agent.acciones.modelos import Accion

    valores = [a.value for a in Accion]
    for v in valores:
        assert "delete" not in v.lower()
        assert "trash" not in v.lower()
        assert "eliminar" not in v.lower()


def test_gmail_adapter_no_tiene_eliminar() -> None:
    """GmailAdapter Protocol no tiene método eliminar."""
    from src.level2_agent.acciones.gmail_adapter import GmailAdapter

    methods = [m for m in dir(GmailAdapter) if not m.startswith("_")]
    for m in methods:
        assert "eliminar" not in m.lower()
        assert "delete" not in m.lower()
        assert "trash" not in m.lower()


def test_ast_gate_no_eliminar() -> None:
    """AST gate: ningún archivo en acciones/ contiene trash/delete/eliminar como identificador."""
    acciones_dir = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "src"
        / "level2_agent"
        / "acciones"
    )
    prohibidas = {"trash", "delete", "eliminar"}
    for py_file in acciones_dir.glob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id.lower() in prohibidas:
                raise AssertionError(
                    f"{py_file.name}: identificador prohibido '{node.id}' (línea {node.lineno})")
            if isinstance(node, ast.Attribute) and node.attr.lower() in prohibidas:
                raise AssertionError(
                    f"{py_file.name}: atributo prohibido '{node.attr}' (línea {node.lineno})")
