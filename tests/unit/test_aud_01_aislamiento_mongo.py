"""Auditoría AUD-01: idempotencia de acciones aislada de MongoDB real.

Defecto detectado (auditoría 2026-11-17): `_ya_procesado` y
`_registrar_procesado` (acciones/ejecutor.py) consultan la colección real
`phishguard.acciones_ejecutadas` cuando `MONGODB_ATLAS_CLUSTER_URI` está en
el entorno (load_dotenv se ejecuta al importar módulos de la suite).

Consecuencias observadas:
- Los tests escriben en la BD de producción (documentos `msg_test_001`,
  `msg_sin_ind`, `msg_001`, `msg_002`, `api_*` hallados en la BD real).
- `test_ac_act_01_dry_run::test_dry_run_malicioso` FALLA en la suite
  completa (motivo `idempotencia`) y PASA aislado: la suite depende del
  estado externo de la BD.

Estas pruebas fijan el contrato de aislamiento y degradación.
"""

from __future__ import annotations

from datetime import UTC, datetime

from dobles_acciones import GmailDoble, JiraDoble, entrada_acciones_ejemplo

TS = datetime(2026, 1, 1, tzinfo=UTC)


def _limpiar(uri_pres: bool, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Prepara entorno: limpia store in-memory y controla la URI de Mongo."""
    from src.level2_agent.acciones.ejecutor import _procesados

    _procesados.clear()
    if uri_pres:
        monkeypatch.setenv("MONGODB_ATLAS_CLUSTER_URI", "mongodb://127.0.0.1:1/")
    else:
        monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)


def test_idempotencia_en_memoria_sin_uri(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Sin URI: idempotencia funciona en memoria y NUNCA se crea MongoClient."""
    import pymongo

    llamadas = {"n": 0}

    def _bomba(*args: object, **kwargs: object) -> object:
        llamadas["n"] += 1
        raise AssertionError("No debe crearse MongoClient sin URI de Mongo")

    monkeypatch.setattr(pymongo, "MongoClient", _bomba)
    _limpiar(uri_pres=False, monkeypatch=monkeypatch)
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")

    from src.level2_agent.acciones.ejecutor import ejecutar_acciones

    gmail, jira = GmailDoble(), JiraDoble()
    entrada = entrada_acciones_ejemplo(message_id="msg_aud_01")

    r1 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=TS)
    assert all(a.ejecutada for a in r1.acciones), r1
    assert all(a.motivo == "exito" for a in r1.acciones), r1

    r2 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=TS)
    assert all(not a.ejecutada for a in r2.acciones), r2
    assert all(a.motivo == "idempotencia" for a in r2.acciones), r2

    assert llamadas["n"] == 0, "el test tocó MongoClient sin URI"


def test_degrada_a_memoria_si_mongo_cae(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Con URI pero Mongo caído: degrada a memoria sin perder idempotencia."""
    import pymongo

    def _caido(*args: object, **kwargs: object) -> object:
        raise RuntimeError("MongoDB caído (doble de auditoría)")

    monkeypatch.setattr(pymongo, "MongoClient", _caido)
    _limpiar(uri_pres=True, monkeypatch=monkeypatch)
    monkeypatch.setenv("ACCIONES_DRY_RUN", "false")

    from src.level2_agent.acciones.ejecutor import ejecutar_acciones

    gmail, jira = GmailDoble(), JiraDoble()
    entrada = entrada_acciones_ejemplo(message_id="msg_aud_02")

    # No debe lanzar aunque MongoClient falle (except Exception: pass).
    r1 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=TS)
    assert all(a.ejecutada for a in r1.acciones), r1

    # El fallback in-memory sí registró: segunda pasada es idempotente.
    r2 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=TS)
    assert all(a.motivo == "idempotencia" for a in r2.acciones), r2


def test_dry_run_registra_en_memoria_sin_uri(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """DRY_RUN sin URI: simulacro registrado en memoria, sin tocar la BD."""
    import pymongo

    def _bomba(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry_run no debe tocar MongoClient")

    monkeypatch.setattr(pymongo, "MongoClient", _bomba)
    _limpiar(uri_pres=False, monkeypatch=monkeypatch)
    monkeypatch.setenv("ACCIONES_DRY_RUN", "true")

    from src.level2_agent.acciones.ejecutor import ejecutar_acciones

    gmail, jira = GmailDoble(), JiraDoble()
    entrada = entrada_acciones_ejemplo(message_id="msg_aud_03")

    r1 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=TS)
    assert all(a.motivo == "dry_run" for a in r1.acciones), r1
    assert len(gmail.llamadas) == 0 and len(jira.llamadas) == 0

    r2 = ejecutar_acciones(entrada, gmail=gmail, jira=jira, ahora=TS)
    assert all(a.motivo == "idempotencia" for a in r2.acciones), r2
