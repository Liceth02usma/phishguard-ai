"""Dobles de prueba para persistencia y métricas (spec 011).

RepositorioDoble y CacheVTDoble trackean llamadas sin tocar MongoDB.
entrada_persistido_ejemplo() construye un AnalisisPersistido mínimo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.level2_agent.persistencia.modelos import AnalisisPersistido


def entrada_persistido_ejemplo(
    *,
    message_id: str = "msg_test_001",
    origen: str = "gmail",
    veredicto: str = "malicioso",
    ruta: str = "ia",
    score_final: int = 85,
    retroalimentacion: str | None = None,
) -> AnalisisPersistido:
    """Construye un AnalisisPersistido mínimo con valores por defecto."""
    ahora = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    return AnalisisPersistido(
        message_id=message_id,
        origen=origen,  # type: ignore[arg-type]
        modo="produccion",
        fecha=ahora,
        duracion_ms=500,
        correo_enmascarado={
            "remitente": "u***@example.com",
            "asunto": "Verifique su cuenta",
        },
        score_final=score_final,
        ruta=ruta,  # type: ignore[arg-type]
        veredicto=veredicto,  # type: ignore[arg-type]
        nivel_severidad="Alto",
        banderas=["CAB_SPF_FAIL"],
        reglas_aplicadas=[],
        autenticacion={"spf": "fail"},
        urls=["http://evil.com/login"],
        adjuntos_nombres=[],
        version_pesos="v1",
        version_modelo="gemini-2.5-flash-lite",
        retroalimentacion=retroalimentacion,  # type: ignore[arg-type]
        expira_en=ahora + timedelta(days=90),
    )
