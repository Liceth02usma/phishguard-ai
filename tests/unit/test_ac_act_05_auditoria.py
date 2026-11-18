"""AC-ACT-05: cada análisis registra qué acción se ejecutó o simuló.

Aislamiento (auditoría AUD-01): sin delenv de MONGODB_ATLAS_CLUSTER_URI este
test fallaba en suite completa (documento `msg_test_001` en la BD real).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_auditoria_malicioso(monkeypatch: pytest.MonkeyPatch) -> None:
    """Para malicioso, se registran 3 acciones con todos los campos."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    resultado = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=ts)

    assert len(resultado.acciones) == 3
    for a in resultado.acciones:
        assert a.accion is not None
        assert a.destino in ("gmail", "jira")
        assert a.identificador == "msg_test_001"
        assert a.ejecutada is True
        assert a.motivo == "exito"
        assert a.timestamp == ts
    assert resultado.procesado is True


def test_auditoria_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """En DRY_RUN, se registran acciones con ejecutada=False."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "true")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="sospechoso")
    resultado = ejecutar_acciones(
        entrada, gmail=gmail, jira=jira,
        ahora=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert len(resultado.acciones) == 2
    assert all(not a.ejecutada for a in resultado.acciones)
    assert all(a.motivo == "dry_run" for a in resultado.acciones)
