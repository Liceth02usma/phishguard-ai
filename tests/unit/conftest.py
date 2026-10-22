"""Configuración compartida de pytest para las pruebas de las compuertas.

Registra el marker `ac` (Art. II.6) y expone helpers para generar archivos
de prueba temporales, además de los dobles del agente ReAct usados por la
spec 001 (Art. II.5 — sin red real).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# Respuesta determinista del doble del agente ReAct (spec 001, research D7).
REPORTE_FALSO = {
    "resumen": "Análisis del correo bajo revisión por el agente.",
    "analisis_tecnico": "Evidencia contrastada con marcos NIST y OWASP por el doble.",
    "indicadores_phishing": ["patron_sospechoso_uno", "patron_sospechoso_dos"],
    "es_phishing": True,
    "nivel_severidad": "Medio",
    "justificacion_veredicto": "Respuesta fija del doble para pruebas deterministas.",
}


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


class _AgenteReActFalso:
    """Doble del agente ReAct: mismo input → misma respuesta JSON (sin red)."""

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el reporte fijo en el formato que consume analyze_email."""
        from langchain_core.messages import AIMessage

        contenido = json.dumps(REPORTE_FALSO, ensure_ascii=False)
        return {"messages": [AIMessage(content=contenido)]}


@pytest.fixture
def agente_react_falso(monkeypatch: pytest.MonkeyPatch) -> _AgenteReActFalso:
    """Sustituye LLM y agente por dobles deterministas (sin API key ni red)."""
    import src.level2_agent.agent as mod_agent

    monkeypatch.setattr(mod_agent, "_ensure_llm", lambda: None)
    agente = _AgenteReActFalso()
    monkeypatch.setattr(mod_agent, "_get_react_agent", lambda: agente)
    return agente


@pytest.fixture
def sin_red_jira(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sustituye create_jira_ticket por un stub sin efectos externos."""
    import src.level2_agent.agent as mod_agent

    monkeypatch.setattr(
        mod_agent, "create_jira_ticket", lambda reporte: {"simulado": True}
    )


@pytest.fixture
def entorno_sin_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina MONGODB_ATLAS_CLUSTER_URI del entorno de la prueba.

    Mecanismo de rojo de AC-MEM-02 (research D7): con el código actual, la
    ruta del agente llama a get_chat_history y lanza ValueError.
    """
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
