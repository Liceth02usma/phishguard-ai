"""AC-PER-01: un análisis guardado no contiene HTML original,
adjuntos ni correos sin enmascarar (FR-002, I1/I2)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from src.level2_agent.persistencia.guardado import (
    guardar_analisis,
    _verificar_sin_html_adjuntos,
)
from src.level2_agent.persistencia.modelos import AnalisisPersistido
from src.level2_agent.persistencia.repositorio import RepositorioDoble

from dobles_persistencia import entrada_persistido_ejemplo


def test_correo_enmascarado_sin_html() -> None:
    """correo_enmascarado no contiene htmlBody → se guarda OK."""
    repo = RepositorioDoble()
    analisis = entrada_persistido_ejemplo()
    # correo_enmascarado no tiene htmlBody
    assert "htmlBody" not in analisis.correo_enmascarado
    msg_id = guardar_analisis(analisis, repo=repo)
    assert msg_id == "msg_test_001"
    doc = repo.buscar("msg_test_001")
    assert doc is not None
    assert "htmlBody" not in doc.get("correo_enmascarado", {})


def test_correo_con_html_rechazado() -> None:
    """correo_enmascarado con htmlBody → ValueError (I1)."""
    analisis = entrada_persistido_ejemplo()
    analisis.correo_enmascarado["htmlBody"] = "<script>alert(1)</script>"
    with __import__("pytest").raises(ValueError, match="I1"):
        _verificar_sin_html_adjuntos(analisis)


def test_adjunto_con_contenido_rechazado() -> None:
    """correo_enmascarado con adjunto contenido → ValueError (I2)."""
    analisis = entrada_persistido_ejemplo()
    analisis.correo_enmascarado["adjuntos"] = [
        {"nombre": "doc.exe", "contenido": "binary_data"}
    ]
    with __import__("pytest").raises(ValueError, match="I2"):
        _verificar_sin_html_adjuntos(analisis)


def test_persistido_no_tiene_contenido_adjunto() -> None:
    """Documento persistido no tiene campo contenido en adjuntos."""
    repo = RepositorioDoble()
    analisis = entrada_persistido_ejemplo()
    # adjuntos_nombres es lista de strings, no de dicts con contenido
    msg_id = guardar_analisis(analisis, repo=repo)
    doc = repo.buscar(msg_id)
    assert doc is not None
    # Verificar que no hay 'contenido' en ningún adjunto
    adjuntos = doc.get("correo_enmascarado", {}).get("adjuntos", [])
    for adj in adjuntos:
        if isinstance(adj, dict):
            assert "contenido" not in adj
