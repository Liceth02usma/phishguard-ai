"""AC-ACT-01: con DRY_RUN=true no se ejecuta ninguna escritura en Gmail ni Jira."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from src.level2_agent.acciones.modelos import Accion, ResultadoAccion

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_dry_run_malicioso() -> None:
    """DRY_RUN=true → ninguna acción se ejecuta para malicioso."""
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    os.environ["ACCIONES_DRY_RUN"] = "true"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones
        resultado = ejecutar_acciones(
            entrada, gmail=gmail, jira=jira,
            ahora=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert all(not a.ejecutada for a in resultado.acciones)
        assert all(a.motivo == "dry_run" for a in resultado.acciones)
        assert len(gmail.llamadas) == 0
        assert len(jira.llamadas) == 0
    finally:
        del os.environ["ACCIONES_DRY_RUN"]


def test_dry_run_sin_indicadores() -> None:
    """DRY_RUN=true → marcar_leido no se ejecuta."""
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="sin_indicadores", message_id="msg_sin_ind")
    os.environ["ACCIONES_DRY_RUN"] = "true"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones, _procesados
        _procesados.clear()
        resultado = ejecutar_acciones(
            entrada, gmail=gmail, jira=jira,
            ahora=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert len(resultado.acciones) == 1
        assert resultado.acciones[0].accion == Accion.MARCAR_LEIDO
        assert not resultado.acciones[0].ejecutada
    finally:
        del os.environ["ACCIONES_DRY_RUN"]
