"""Orquestador del motor de decisión determinista (spec 008, M09).

Función pura: evaluar_veredicto(EntradaMotor) → VeredictoMotor.
1. Evalúa reglas duras R1–R5 en orden; la primera que aplica fija
   veredicto='malicioso' (FR-001).
2. Si ninguna regla aplicó, evalúa la tabla de decisión FR-002
   (6 condiciones ordenadas).
3. Ensambla VeredictoMotor con veredicto, score_final, nivel_severidad,
   ruta, reglas_aplicadas, banderas y verificaciones_incompletas.

Cero I/O, cero estado, cero azar → determinismo garantizado (AC-DEC-04).
"""

from __future__ import annotations

from src.level2_agent.decision.modelos import (
    EntradaMotor,
    NivelSeveridad,
    ReglaAplicada,
    Ruta,
    Veredicto,
    VeredictoMotor,
)
from src.level2_agent.decision.reglas import evaluar_reglas_duras
from src.level2_agent.decision.tabla import evaluar_tabla


def _severidad_regla_dura(reglas: list[ReglaAplicada]) -> NivelSeveridad:
    """Calcula la severidad cuando una regla dura aplicó (M09.1).

    R1/R2/R5 → Crítico; R3/R4 → Alto.
    SEVERIDAD_REGLA ya tiene el mapeo correcto.
    """
    # Solo se llama cuando reglas_aplicadas no está vacío.
    return reglas[0].severidad


def evaluar_veredicto(entrada: EntradaMotor) -> VeredictoMotor:
    """Motor de decisión determinista (M09).

    1. Evalúa reglas duras R1–R5 en orden; la primera que aplica fija
       veredicto = "malicioso" (FR-001).
    2. Si ninguna regla aplicó, evalúa la tabla de decisión FR-002
       (6 condiciones ordenadas).
    3. Retorna VeredictoMotor con veredicto, score_final, nivel_severidad,
       ruta, reglas_aplicadas, banderas y verificaciones_incompletas.
    """
    # Paso 1: evaluar reglas duras
    reglas_aplicadas = evaluar_reglas_duras(entrada)

    if reglas_aplicadas:
        # Una regla dura aplicó → malicioso por reglas
        veredicto: Veredicto = "malicioso"
        severidad: NivelSeveridad = _severidad_regla_dura(reglas_aplicadas)
        ruta: Ruta = "reglas"
    else:
        # Paso 2: evaluar tabla de decisión
        veredicto, severidad, ruta = evaluar_tabla(entrada)

    # Paso 3: ensamblar VeredictoMotor
    return VeredictoMotor(
        veredicto=veredicto,
        score_final=entrada.score_final.score_final,
        nivel_severidad=severidad,
        ruta=ruta,
        reglas_aplicadas=reglas_aplicadas,
        banderas=entrada.banderas_cabeceras,
        verificaciones_incompletas=entrada.verificaciones_incompletas,
    )
