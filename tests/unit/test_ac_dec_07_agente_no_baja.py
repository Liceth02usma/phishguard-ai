"""AC-DEC-07: la opinión del agente puede subir el riesgo, nunca bajar una regla dura.

FR-004: si una regla dura fijó malicioso, el agente diciendo False
(no phishing) NO puede bajar el veredicto.
"""

from __future__ import annotations

from src.level2_agent.virustotal.modelos import (
    LastAnalysisStats,
    ResultadoVT,
)

from dobles_decision import entrada_ejemplo


def _vt_maliciosa_archivo() -> ResultadoVT:
    return ResultadoVT(
        tipo="archivo",
        identificador="a" * 64,
        clasificacion="maliciosa",
        fuente="cache",
        stats=LastAnalysisStats(malicious=10, suspicious=0, undetected=0, harmless=0),
        consultas_externas=0,
    )


def test_r1_activa_agente_en_contra() -> None:
    """R1 activa + agente=False → veredicto sigue malicioso."""
    entrada = entrada_ejemplo(
        resultados_vt=[_vt_maliciosa_archivo()],
        confirmacion_agente=False,
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "malicioso"
    assert resultado.ruta == "reglas"
    assert any(r.id == "R1" for r in resultado.reglas_aplicadas)


def test_r1_activa_agente_none() -> None:
    """R1 activa + agente=None → veredicto sigue malicioso."""
    entrada = entrada_ejemplo(
        resultados_vt=[_vt_maliciosa_archivo()],
        confirmacion_agente=None,
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "malicioso"


def test_agente_confirma_sin_regla_dura() -> None:
    """Sin regla dura + agente confirma → malicioso por ia (sube riesgo)."""
    entrada = entrada_ejemplo(score=50, confirmacion_agente=True)
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "malicioso"
    assert resultado.ruta == "ia"


def test_agente_no_confirma_sin_regla_dura() -> None:
    """Sin regla dura + agente no confirma → sospechoso (no sube a malicioso)."""
    entrada = entrada_ejemplo(score=50, confirmacion_agente=False)
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "sospechoso"
