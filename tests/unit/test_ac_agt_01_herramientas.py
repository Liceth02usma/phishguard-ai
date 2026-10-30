"""AC-AGT-01: la lista de herramientas del agente es exactamente [busqueda_vectorial].

Se verifica que el agente ReAct no tiene check_ip_reputation ni
jira_integration como herramientas. Solo busqueda_vectorial (RAG).
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from src.level2_agent.agente.agente import _construir_herramientas

from dobles_agente import ModeloDoble  # AC-AGT-06: usa doble


def _mock_retriever() -> MagicMock:
    """Crea un retriever simulado para las pruebas."""
    retriever = MagicMock()
    retriever.invoke.return_value = []
    return retriever


def test_herramientas_solo_busqueda_vectorial() -> None:
    """La lista de herramientas es exactamente [busqueda_vectorial]."""
    with patch("src.level2_agent.agente.agente.create_retriever", return_value=_mock_retriever()):
        herramientas = _construir_herramientas()
        nombres = [h.name for h in herramientas]
        assert nombres == ["busqueda_vectorial"], (
            f"Herramientas esperadas: ['busqueda_vectorial'], obtenidas: {nombres}"
        )


def test_no_hay_ip_reputation() -> None:
    """check_ip_reputation no está en las herramientas del agente."""
    with patch("src.level2_agent.agente.agente.create_retriever", return_value=_mock_retriever()):
        herramientas = _construir_herramientas()
        nombres = [h.name for h in herramientas]
        assert "check_ip_reputation" not in nombres


def test_no_hay_jira() -> None:
    """jira_integration no está en las herramientas del agente."""
    with patch("src.level2_agent.agente.agente.create_retriever", return_value=_mock_retriever()):
        herramientas = _construir_herramientas()
        nombres = [h.name for h in herramientas]
        assert "jira_integration" not in nombres
        assert "create_jira_ticket" not in nombres
