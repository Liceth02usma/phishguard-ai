"""AC-DEC-04: determinismo — mismo input produce mismo output.

Propiedad: evaluar_veredicto es una función pura. Llamada N veces con
la misma entrada, produce exactamente el mismo VeredictoMotor.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from dobles_decision import entrada_ejemplo


def test_determinismo_manual() -> None:
    """La misma entrada evaluada 10 veces da el mismo resultado."""
    entrada = entrada_ejemplo(score=55, confirmacion_agente=True)
    from src.level2_agent.decision.motor import evaluar_veredicto

    primer_resultado = evaluar_veredicto(entrada)
    for _ in range(9):
        resultado = evaluar_veredicto(entrada)
        assert resultado == primer_resultado


@settings(max_examples=20)
@given(score=st.integers(min_value=0, max_value=100))
def test_determinismo_hypothesis(score: int) -> None:
    """Propiedad: mismo score → mismo veredicto (10 evaluaciones)."""
    entrada = entrada_ejemplo(score=score)
    from src.level2_agent.decision.motor import evaluar_veredicto

    primer_resultado = evaluar_veredicto(entrada)
    for _ in range(9):
        assert evaluar_veredicto(entrada) == primer_resultado


@settings(max_examples=10)
@given(
    score=st.integers(min_value=0, max_value=100),
    agente=st.one_of(st.none(), st.booleans()),
)
def test_determinismo_con_agente(score: int, agente: bool | None) -> None:
    """Propiedad: mismo score + agente → mismo veredicto."""
    entrada = entrada_ejemplo(score=score, confirmacion_agente=agente)
    from src.level2_agent.decision.motor import evaluar_veredicto

    r1 = evaluar_veredicto(entrada)
    r2 = evaluar_veredicto(entrada)
    assert r1 == r2
