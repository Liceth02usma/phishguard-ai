"""AC-ACT-02: procesar dos veces el mismo message_id ejecuta acciones una sola vez."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_idempotencia_mismo_message_id() -> None:
    """Segunda llamada con mismo message_id → idempotencia, sin re-ejecutar."""
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="malicioso", message_id="msg_001")
    os.environ["ACCIONES_DRY_RUN"] = "false"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones, _procesados
        _procesados.clear()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Primera llamada
        r1 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=ts)
        assert all(a.ejecutada for a in r1.acciones)
        first_gmail_calls = len(gmail.llamadas)
        first_jira_calls = len(jira.llamadas)

        # Segunda llamada (mismo message_id)
        r2 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=ts)
        assert all(not a.ejecutada for a in r2.acciones)
        assert all(a.motivo == "idempotencia" for a in r2.acciones)
        # No se hicieron más llamadas
        assert len(gmail.llamadas) == first_gmail_calls
        assert len(jira.llamadas) == first_jira_calls
    finally:
        del os.environ["ACCIONES_DRY_RUN"]


def test_idempotencia_message_id_diferente() -> None:
    """Message_id diferente → se ejecutan acciones normalmente."""
    gmail = GmailDoble()
    jira = JiraDoble()
    os.environ["ACCIONES_DRY_RUN"] = "false"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones, _procesados
        _procesados.clear()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

        e1 = entrada_acciones_ejemplo(veredicto="malicioso", message_id="msg_001")
        e2 = entrada_acciones_ejemplo(veredicto="malicioso", message_id="msg_002")

        r1 = ejecutar_acciones(e1, gmail=gmail, jira=jira, ahora=ts)
        r2 = ejecutar_acciones(e2, gmail=gmail, jira=jira, ahora=ts)
        assert all(a.ejecutada for a in r1.acciones)
        assert all(a.ejecutada for a in r2.acciones)
    finally:
        del os.environ["ACCIONES_DRY_RUN"]
