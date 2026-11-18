"""AC-ACT-02: procesar dos veces el mismo message_id ejecuta acciones una sola vez.

Aislamiento (auditoría AUD-01): sin delenv de MONGODB_ATLAS_CLUSTER_URI este
test fallaba en suite completa porque `_ya_procesado` encontraba en la BD real
los documentos `msg_001`/`msg_002` dejados por corridas previas.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_idempotencia_mismo_message_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Segunda llamada con mismo message_id → idempotencia, sin re-ejecutar."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="malicioso", message_id="msg_001")
    ts = datetime(2026, 1, 1, tzinfo=UTC)

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


def test_idempotencia_message_id_diferente(monkeypatch: pytest.MonkeyPatch) -> None:
    """Message_id diferente → se ejecutan acciones normalmente."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble()
    ts = datetime(2026, 1, 1, tzinfo=UTC)

    e1 = entrada_acciones_ejemplo(veredicto="malicioso", message_id="msg_001")
    e2 = entrada_acciones_ejemplo(veredicto="malicioso", message_id="msg_002")

    r1 = ejecutar_acciones(e1, gmail=gmail, jira=jira, ahora=ts)
    r2 = ejecutar_acciones(e2, gmail=gmail, jira=jira, ahora=ts)
    assert all(a.ejecutada for a in r1.acciones)
    assert all(a.ejecutada for a in r2.acciones)
