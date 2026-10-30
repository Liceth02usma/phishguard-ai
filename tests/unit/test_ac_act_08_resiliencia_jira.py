"""AC-ACT-08: si Jira falla, la acción de Gmail se mantiene, error se registra."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_jira_falla_gmail_se_mantiene() -> None:
    """Jira ConnectionError → Gmail ejecuta, Jira registra error, no exception."""
    gmail = GmailDoble()
    jira = JiraDoble(fallar=True)
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    os.environ["ACCIONES_DRY_RUN"] = "false"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones, _procesados
        _procesados.clear()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # No debe lanzar excepción
        resultado = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=ts)

        # Gmail actions deben haberse ejecutado
        gmail_acciones = [a for a in resultado.acciones if a.destino == "gmail"]
        assert len(gmail_acciones) >= 1
        assert all(a.ejecutada for a in gmail_acciones)

        # Jira action debe tener error
        jira_acciones = [a for a in resultado.acciones if a.destino == "jira"]
        assert len(jira_acciones) >= 1
        assert all(a.motivo == "error_jira" for a in jira_acciones)
        assert all(not a.ejecutada for a in jira_acciones)
    finally:
        del os.environ["ACCIONES_DRY_RUN"]


def test_jira_falla_no_bucle() -> None:
    """Jira falla → no se reintenta (no bucle)."""
    gmail = GmailDoble()
    jira = JiraDoble(fallar=True)
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    os.environ["ACCIONES_DRY_RUN"] = "false"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones, _procesados
        _procesados.clear()
        resultado = ejecutar_acciones(
            entrada, gmail=gmail, jira=jira,
            ahora=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        # Solo 1 intento de Jira (crear_ticket llamado 1 vez)
        crear_calls = [c for c in jira.llamadas if c[0] == "crear_ticket"]
        assert len(crear_calls) == 1
    finally:
        del os.environ["ACCIONES_DRY_RUN"]
