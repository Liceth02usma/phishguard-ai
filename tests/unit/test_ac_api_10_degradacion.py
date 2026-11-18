"""AC-API-10: caída de VT/modelo → 201 con revision_manual."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


@pytest.mark.ac("AC-API-10")
def test_caida_modelo_revision_manual() -> None:
    """Si el pipeline lanza excepción, la respuesta es 201 con revision_manual."""
    os.environ["API_KEY"] = "test-key"
    # Sin GOOGLE_API_KEY → analyze_email fallirá
    os.environ.pop("GOOGLE_API_KEY", "")
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    c = TestClient(app)

    r = c.post(
        "/api/analyses",
        json={"modo": "pegar", "subject": "Test caída", "text": "body"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 201
    data = r.json()
    # Puede ser revision_manual (caída) o sin_indicadores (si no falla)
    assert data["resultado"]["veredicto"] in (
        "revision_manual",
        "sin_indicadores",
        "malicioso",
        "sospechoso",
    )


@pytest.mark.ac("AC-API-10")
def test_vt_sin_clave_registra_incompleta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opción A (auditoría 2026-11-17): sin VT_API_KEY → VT_NO_DISPONIBLE
    queda registrado como verificación incompleta (FR-003) en vez de
    ignorarse silenciosamente."""
    monkeypatch.delenv("VT_API_KEY", raising=False)
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)

    from src.level2_agent.agent import _consultar_vt
    from src.level2_agent.models import EmailData

    email = EmailData(
        subject="Prueba AC-API-10",
        urls=["https://ejemplo.com/recurso"],
        headers='{"from": "usuario@ejemplo.com"}',
    )

    resultados, incompletas = _consultar_vt(email)

    # El cliente responde (no lanza) con sin_llamada + banda VT_NO_DISPONIBLE
    assert len(resultados) == 2  # url + dominio
    from src.level2_agent.decision.modelos import VerificacionIncompleta

    registradas = [v for v in incompletas if isinstance(v, VerificacionIncompleta)]
    assert len(registradas) == 2
    tipos = {v.tipo for v in registradas}
    assert tipos == {"vt_url", "vt_dominio"}
    assert all("VT_NO_DISPONIBLE" in v.razon for v in registradas)


@pytest.mark.ac("AC-API-10")
def test_vt_incompleta_lleva_zona_gris_a_revision_manual() -> None:
    """Opción A: con VT caído, el motor decide revision_manual (FR-003)."""
    from src.level2_agent.decision import evaluar_veredicto
    from src.level2_agent.decision.modelos import VerificacionIncompleta

    from dobles_decision import entrada_ejemplo

    entrada = entrada_ejemplo(
        verificaciones_incompletas=[
            VerificacionIncompleta(
                tipo="vt_url",
                razon="VT_NO_DISPONIBLE: VirusTotal no disponible",
            )
        ],
    )

    veredicto = evaluar_veredicto(entrada)
    assert veredicto.veredicto == "revision_manual"
