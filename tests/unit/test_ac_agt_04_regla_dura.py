"""AC-AGT-04: el agente no puede bajar un veredicto de regla dura.

Verificado junto con la spec 08: si una regla dura fijÃ³ malicioso,
la opiniÃ³n del agente (confirmacion_agente=False) no puede cambiar
el veredicto a uno menor. El motor de decisiÃ³n (spec 08) lo garantiza.
"""

from __future__ import annotations

from src.level2_agent.agente.modelos import SalidaAgente
from src.level2_agent.decision.modelos import EntradaMotor
from src.level2_agent.models import EmailData
from src.level2_agent.virustotal.modelos import (
    LastAnalysisStats,
    ResultadoVT,
)
from src.level3_logic.scoring.modelos import ScoreFinal

from dobles_agente import ContadorDoble, ModeloDoble, entrada_agente_ejemplo


def test_regla_dura_r1_agente_en_contra() -> None:
    """R1 activa + agente dice no phishing â†’ veredicto sigue malicioso."""
    vt_mal = ResultadoVT(
        tipo="archivo",
        identificador="a" * 64,
        clasificacion="maliciosa",
        fuente="cache",
        stats=LastAnalysisStats(
            malicious=10, suspicious=0, undetected=0, harmless=0
        ),
        consultas_externas=0,
    )

    # El agente opina que NO es phishing
    modelo = ModeloDoble(
        salida=SalidaAgente(
            resumen="No es phishing",
            analisis_tecnico="AnÃ¡lisis tÃ©cnico",
            es_phishing=False,
            indicadores_phishing=[],
            nivel_severidad="Bajo",
            justificacion_veredicto="No hay indicadores suficientes",
        )
    )

    entrada = entrada_agente_ejemplo(score=10, resultados_vt=[vt_mal])
    from src.level2_agent.agente.agente import consultar_agente

    # Contador aislado: el tope diario real (Mongo) no debe condicionar.
    resultado_agente = consultar_agente(
        entrada, modelo=modelo, contador=ContadorDoble()  # type: ignore[arg-type]
    )

    # Pasar al motor de decisiÃ³n con confirmacion_agente=False
    from src.level2_agent.decision.motor import evaluar_veredicto

    entrada_motor = EntradaMotor(
        email_data=EmailData(),
        score_final=ScoreFinal(
            score_final=10, score_clasificador=10.0,
            puntos_banderas=0, version_modelo="test",
        ),
        resultados_vt=[vt_mal],
        confirmacion_agente=resultado_agente.confirmacion_agente,
    )
    veredicto = evaluar_veredicto(entrada_motor)
    assert veredicto.veredicto == "malicioso", (
        f"Regla dura R1 + agente en contra: veredicto={veredicto.veredicto}"
    )
    assert veredicto.ruta == "reglas"
