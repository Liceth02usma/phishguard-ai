"""AC-ACT-05: cada análisis registra qué acción se ejecutó o simuló."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo


def test_auditoria_malicioso() -> None:
    """Para malicioso, se registran 3 acciones con todos los campos."""
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="malicioso")
    os.environ["ACCIONES_DRY_RUN"] = "false"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones, _procesados
        _procesados.clear()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
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
    finally:
        del os.environ["ACCIONES_DRY_RUN"]


def test_auditoria_dry_run() -> None:
    """En DRY_RUN, se registran acciones con ejecutada=False."""
    gmail = GmailDoble()
    jira = JiraDoble()
    entrada = entrada_acciones_ejemplo(veredicto="sospechoso")
    os.environ["ACCIONES_DRY_RUN"] = "true"
    try:
        from src.level2_agent.acciones.ejecutor import ejecutar_acciones, _procesados
        _procesados.clear()
        resultado = ejecutar_acciones(
            entrada, gmail=gmail, jira=jira,
            ahora=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert len(resultado.acciones) == 2
        assert all(not a.ejecutada for a in resultado.acciones)
        assert all(a.motivo == "dry_run" for a in resultado.acciones)
    finally:
        del os.environ["ACCIONES_DRY_RUN"]
