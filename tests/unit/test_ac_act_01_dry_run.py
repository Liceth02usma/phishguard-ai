"""AC-ACT-01: con DRY_RUN=true no se ejecuta ninguna escritura en Gmail ni Jira.

Aislamiento (auditoría AUD-01): este test FALLABA en la suite completa y
pasaba aislado porque `_ya_procesado` consultaba la BD real de MongoDB
(documento `msg_test_001` dejado por corridas previas con DRY_RUN=false).
Ahora se elimina la URI del entorno y se limpia el store in-memory.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.level2_agent.acciones.modelos import Accion

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_dry_run_malicioso(monkeypatch: pytest.MonkeyPatch) -> None:
    """DRY_RUN=true → ninguna acción se ejecuta para malicioso."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "true")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    resultado = ejecutar_acciones(
        entrada, gmail=gmail, jira=jira,
        ahora=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert all(not a.ejecutada for a in resultado.acciones)
    assert all(a.motivo == "dry_run" for a in resultado.acciones)
    assert len(gmail.llamadas) == 0
    assert len(jira.llamadas) == 0


def test_dry_run_sin_indicadores(monkeypatch: pytest.MonkeyPatch) -> None:
    """DRY_RUN=true → marcar_leido no se ejecuta."""
    monkeypatch.setenv("ACCIONES_DRY_RUN", "true")
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)
    from src.level2_agent.acciones.ejecutor import _procesados, ejecutar_acciones

    _procesados.clear()
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="sin_indicadores", message_id="msg_sin_ind")
    resultado = ejecutar_acciones(
        entrada, gmail=gmail, jira=jira,
        ahora=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert len(resultado.acciones) == 1
    assert resultado.acciones[0].accion == Accion.MARCAR_LEIDO
    assert not resultado.acciones[0].ejecutada
