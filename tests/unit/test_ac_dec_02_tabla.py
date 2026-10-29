"""AC-DEC-02: tabla de decisión probada en sus límites (score 29/30/75/76).

M09 define 6 filas en la tabla de decisión. Este archivo prueba los
valores límite del score (29, 30, 75, 76) con y sin confirmación del
agente, verificando el veredicto, severidad y ruta correctos.
"""

from __future__ import annotations

import pytest

from dobles_decision import entrada_ejemplo


@pytest.mark.parametrize(
    "score, confirmacion, veredicto_esperado, severidad_esperada, ruta_esperada",
    [
        # score < 30 → sin_indicadores (si no hay banderas)
        (29, None, "sin_indicadores", "Bajo", "heuristica"),
        (29, True, "sin_indicadores", "Bajo", "heuristica"),
        (29, False, "sin_indicadores", "Bajo", "heuristica"),
        # score 30–75 sin agente → sospechoso
        (30, None, "sospechoso", "Medio", "heuristica"),
        (30, False, "sospechoso", "Medio", "heuristica"),
        (75, None, "sospechoso", "Medio", "heuristica"),
        (75, False, "sospechoso", "Medio", "heuristica"),
        # score 30–75 con agente confirmando → malicioso por ia
        (30, True, "malicioso", "Alto", "ia"),
        (50, True, "malicioso", "Alto", "ia"),
        (75, True, "malicioso", "Alto", "ia"),
        # score >= 76 → malicioso por heurística
        (76, None, "malicioso", "Alto", "heuristica"),
        (76, True, "malicioso", "Alto", "heuristica"),
        (76, False, "malicioso", "Alto", "heuristica"),
        (100, None, "malicioso", "Alto", "heuristica"),
    ],
)
def test_tabla_decision_limites(
    score: int,
    confirmacion: bool | None,
    veredicto_esperado: str,
    severidad_esperada: str,
    ruta_esperada: str,
) -> None:
    """Prueba la tabla de decisión en los límites del score."""
    entrada = entrada_ejemplo(score=score, confirmacion_agente=confirmacion)
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == veredicto_esperado, (
        f"score={score}, agente={confirmacion}: "
        f"veredicto {resultado.veredicto} != {veredicto_esperado}"
    )
    assert resultado.nivel_severidad == severidad_esperada, (
        f"score={score}, agente={confirmacion}: "
        f"severidad {resultado.nivel_severidad} != {severidad_esperada}"
    )
    assert resultado.ruta == ruta_esperada, (
        f"score={score}, agente={confirmacion}: "
        f"ruta {resultado.ruta} != {ruta_esperada}"
    )


def test_score_bajo_con_bandera_alta() -> None:
    """Score < 30 pero con bandera alta → sospechoso (fila 5 de la tabla)."""
    from src.level2_agent.banderas.modelos import BanderaActivada

    entrada = entrada_ejemplo(
        score=10,
        banderas_cabeceras=[
            BanderaActivada(
                codigo="DMARC_FALLA",
                severidad="alta",
                puntos=15,
                detalle="DMARC falla",
            ),
        ],
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    assert resultado.veredicto == "sospechoso"
    assert resultado.nivel_severidad == "Medio"
    assert resultado.ruta == "heuristica"
