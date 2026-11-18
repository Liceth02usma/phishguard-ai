"""AC-DEC-03: con VT caído y sin otras señales, el veredicto NUNCA es sin_indicadores.

FR-003: si una verificación obligatoria quedó incompleta, el motor
debe producir revision_manual, nunca sin_indicadores.
"""

from __future__ import annotations

from src.level2_agent.decision.modelos import VerificacionIncompleta

from dobles_decision import entrada_ejemplo


def test_vt_caido_revision_manual() -> None:
    """Con VT caído (verificación incompleta) → revision_manual."""
    entrada = entrada_ejemplo(
        score=5,
        verificaciones_incompletas=[
            VerificacionIncompleta(tipo="vt_adjunto", razon="VT_NO_DISPONIBLE"),
        ],
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "revision_manual"
    assert resultado.nivel_severidad == "Medio"


def test_vt_sin_cuota_revision_manual() -> None:
    """Con VT sin cuota → revision_manual."""
    entrada = entrada_ejemplo(
        score=5,
        verificaciones_incompletas=[
            VerificacionIncompleta(tipo="vt_url", razon="VT_PRESUPUESTO_AGOTADO"),
        ],
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "revision_manual"


def test_expansion_url_fallida_revision_manual() -> None:
    """Con expansión de URL fallida → revision_manual."""
    entrada = entrada_ejemplo(
        score=5,
        verificaciones_incompletas=[
            VerificacionIncompleta(tipo="expansion_url", razon="limite_excedido"),
        ],
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "revision_manual"


def test_verificacion_incompleta_nunca_sin_indicadores() -> None:
    """Cualquier verificación incompleta impide sin_indicadores."""
    for tipo in ("vt_adjunto", "vt_url", "vt_dominio", "vt_ip", "expansion_url"):
        entrada = entrada_ejemplo(
            score=0,
            verificaciones_incompletas=[
                VerificacionIncompleta(tipo=tipo, razon="test"),
            ],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert resultado.veredicto != "sin_indicadores", (
            f"tipo={tipo}: veredicto fue sin_indicadores con verificación incompleta"
        )


def test_verificacion_incompleta_prevalece_sobre_score_alto() -> None:
    """Incluso con score 90, si hay verificación incompleta → revision_manual."""
    entrada = entrada_ejemplo(
        score=90,
        verificaciones_incompletas=[
            VerificacionIncompleta(tipo="vt_adjunto", razon="VT_NO_DISPONIBLE"),
        ],
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "revision_manual"
