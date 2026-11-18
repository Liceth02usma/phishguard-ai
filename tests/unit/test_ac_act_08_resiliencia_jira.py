"""AC-ACT-08: si Jira falla, la acción de Gmail se mantiene, error se registra.

Aislamiento (auditoría AUD-01): sin delenv de MONGODB_ATLAS_CLUSTER_URI este
test fallaba en suite completa (documento `msg_test_001` en la BD real).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_jira_falla_gmail_se_mantiene(monkeypatch: pytest.MonkeyPatch) -> None:
    """Jira ConnectionError → Gmail ejecuta, Jira registra error, no exception."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble(fallar=True)
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    ts = datetime(2026, 1, 1, tzinfo=UTC)

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


def test_jira_falla_no_bucle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Jira falla → no se reintenta (no bucle)."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble(fallar=True)
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    ejecutar_acciones(
        entrada, gmail=gmail, jira=jira,
        ahora=datetime(2026, 1, 1, tzinfo=UTC),
    )
    # Solo 1 intento de Jira (crear_ticket llamado 1 vez)
    crear_calls = [c for c in jira.llamadas if c[0] == "crear_ticket"]
    assert len(crear_calls) == 1
