"""AC-DEC-06: 100 % de cobertura de ramas en motor.py.

Este archivo ejercita explícitamente los caminos de código del
orquestador para complementar la compuerta de cobertura en verify.py.
Cada rama del motor (regla dura sí/no, tabla fila 1–6) se prueba
directamente.
"""

from __future__ import annotations

from src.level2_agent.adjuntos.modelos import BanderaAdjunto
from src.level2_agent.banderas.modelos import (
    BanderaActivada,
    EstadosAutenticacion,
)
from src.level2_agent.decision.modelos import VerificacionIncompleta
from src.level2_agent.virustotal.modelos import (
    LastAnalysisStats,
    ResultadoVT,
)

from dobles_decision import entrada_ejemplo


def _vt_maliciosa(tipo: str, id_: str) -> ResultadoVT:
    return ResultadoVT(
        tipo=tipo,
        identificador=id_,
        clasificacion="maliciosa",
        fuente="cache",
        stats=LastAnalysisStats(malicious=10, suspicious=0, undetected=0, harmless=0),
        consultas_externas=0,
    )


def test_rama_regla_dura_aplica() -> None:
    """Rama: al menos una regla dura aplica → malicioso por reglas."""
    entrada = entrada_ejemplo(resultados_vt=[_vt_maliciosa("archivo", "a" * 64)])
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "malicioso" and r.ruta == "reglas"


def test_rama_ninguna_regla_aplica() -> None:
    """Rama: ninguna regla dura aplica → se evalúa la tabla."""
    entrada = entrada_ejemplo(score=50)
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.ruta != "reglas"


def test_rama_tabla_fila1_verificacion_incompleta() -> None:
    """Tabla fila 1: verificación incompleta → revision_manual."""
    entrada = entrada_ejemplo(
        score=50,
        verificaciones_incompletas=[
            VerificacionIncompleta(tipo="vt_adjunto", razon="test"),
        ],
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "revision_manual"


def test_rama_tabla_fila2_score_alto() -> None:
    """Tabla fila 2: score >= 76 → malicioso heurística."""
    entrada = entrada_ejemplo(score=76)
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "malicioso" and r.ruta == "heuristica"


def test_rama_tabla_fila3_agente_confirma() -> None:
    """Tabla fila 3: score 30–75 + agente confirma → malicioso ia."""
    entrada = entrada_ejemplo(score=50, confirmacion_agente=True)
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "malicioso" and r.ruta == "ia"


def test_rama_tabla_fila4_agente_no_confirma() -> None:
    """Tabla fila 4: score 30–75 + agente no confirma → sospechoso."""
    entrada = entrada_ejemplo(score=50, confirmacion_agente=False)
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "sospechoso"


def test_rama_tabla_fila4_agente_no_consultado() -> None:
    """Tabla fila 4: score 30–75 + agente None → sospechoso."""
    entrada = entrada_ejemplo(score=50, confirmacion_agente=None)
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "sospechoso"


def test_rama_tabla_fila5_score_bajo_con_bandera() -> None:
    """Tabla fila 5: score < 30 + bandera alta → sospechoso."""
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

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "sospechoso"


def test_rama_tabla_fila6_sin_indicadores() -> None:
    """Tabla fila 6: score < 30 + sin banderas + verificaciones completas → sin_indicadores."""
    entrada = entrada_ejemplo(score=10)
    from src.level2_agent.decision.motor import evaluar_veredicto

    r = evaluar_veredicto(entrada)
    assert r.veredicto == "sin_indicadores"
