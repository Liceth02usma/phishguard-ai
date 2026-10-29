"""Dobles de prueba para el motor de decisión (spec 008).

Factory de EntradaMotor con valores por defecto sensibles para pruebas
unitarias. Cero I/O, cero red.
"""

from __future__ import annotations

from src.level2_agent.banderas.modelos import (
    BanderaActivada,
    EstadosAutenticacion,
)
from src.level2_agent.decision.modelos import EntradaMotor, VerificacionIncompleta
from src.level2_agent.models import EmailData
from src.level3_logic.scoring.modelos import ScoreFinal


def entrada_ejemplo(
    *,
    score: int = 50,
    confirmacion_agente: bool | None = None,
    verificaciones_incompletas: list[VerificacionIncompleta] | None = None,
    banderas_cabeceras: list[BanderaActivada] | None = None,
    estados_autenticacion: EstadosAutenticacion | None = None,
    resultados_vt: list[object] | None = None,
    resultado_adjuntos: list[object] | None = None,
    email_data: EmailData | None = None,
) -> EntradaMotor:
    """Construye una EntradaMotor mínima con valores por defecto.

    Todos los parámetros son keyword-only para evitar errores de posición.
    Los valores por defecto representan un correo sin indicadores:
    score 50, sin banderas, sin VT, agente no consultado, verificaciones
    completas.
    """
    from src.level2_agent.virustotal.modelos import ResultadoVT

    return EntradaMotor(
        email_data=email_data or EmailData(),
        score_final=ScoreFinal(
            score_final=score,
            score_clasificador=float(score),
            puntos_banderas=0,
            version_modelo="test",
        ),
        banderas_cabeceras=banderas_cabeceras or [],
        estados_autenticacion=estados_autenticacion or EstadosAutenticacion(),
        resultado_adjuntos=resultado_adjuntos or [],
        resultados_vt=resultados_vt or [],
        confirmacion_agente=confirmacion_agente,
        verificaciones_incompletas=verificaciones_incompletas or [],
    )
