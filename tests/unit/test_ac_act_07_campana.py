"""AC-ACT-07: dos correos de la misma campaña crean un solo ticket.

Aislamiento (auditoría AUD-01): sin delenv de MONGODB_ATLAS_CLUSTER_URI este
test fallaba en suite completa (documentos `msg_001`/`msg_002` en la BD real).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_campana_misma_huella(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dos correos con misma huella → segundo se vincula al ticket del primero."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble()
    ts = datetime(2026, 1, 1, tzinfo=UTC)

    # Primer correo de la campaña
    e1 = entrada_acciones_ejemplo(
        veredicto="malicioso", message_id="msg_001",
        remitente="phisher@evil.com", asunto="Verifique su cuenta",
        urls=["http://evil.com/login"],
    )
    r1 = ejecutar_acciones(e1, gmail=gmail, jira=jira, ahora=ts)
    assert r1.ticket_key is not None
    first_key = r1.ticket_key

    # Segundo correo de la misma campaña (mismo remitente + asunto + dominio)
    jira._ticket_existente = first_key  # Simular que Jira ya tiene el ticket
    e2 = entrada_acciones_ejemplo(
        veredicto="malicioso", message_id="msg_002",
        remitente="phisher@evil.com", asunto="Verifique su cuenta",
        urls=["http://evil.com/login"],
    )
    ejecutar_acciones(e2, gmail=gmail, jira=jira, ahora=ts)

    # Verificar que se vinculó en vez de crear nuevo
    vincular_calls = [c for c in jira.llamadas if c[0] == "vincular"]
    assert len(vincular_calls) >= 1


def test_huella_diferente() -> None:
    """Correos con huella diferente → se crean tickets separados."""
    from src.level2_agent.acciones.huella import calcular_huella

    h1 = calcular_huella("a@evil.com", "Asunto 1", ["http://evil1.com"])
    h2 = calcular_huella("b@other.com", "Asunto 2", ["http://other.com"])
    assert h1 != h2
