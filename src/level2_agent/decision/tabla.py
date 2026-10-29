"""Tabla de decisión del motor (spec 008, M09, FR-002).

6 filas ordenadas que se evalúan cuando ninguna regla dura aplicó.
Cada fila es un predicado sobre (score, agente, verificaciones, banderas)
que produce (veredicto, severidad, ruta).

Art. VI.2: las condiciones y umbrales son LITERALES de M09.
"""

from __future__ import annotations

from src.level2_agent.decision.modelos import (
    UMBRAL_ALTO,
    UMBRAL_BAJO,
    EntradaMotor,
    NivelSeveridad,
    Ruta,
    Veredicto,
)


def _hay_verificacion_incompleta(entrada: EntradaMotor) -> bool:
    """Fila 1: alguna verificación obligatoria no se pudo completar."""
    return len(entrada.verificaciones_incompletas) > 0


def _score_alto(entrada: EntradaMotor) -> bool:
    """Fila 2: score_final >= 76 → malicioso directo."""
    return entrada.score_final.score_final >= UMBRAL_ALTO


def _score_medio_agente_confirma(entrada: EntradaMotor) -> bool:
    """Fila 3: score 30–75 Y agente confirma phishing."""
    score = entrada.score_final.score_final
    return UMBRAL_BAJO <= score <= (UMBRAL_ALTO - 1) and entrada.confirmacion_agente is True


def _score_medio_agente_no_confirma(entrada: EntradaMotor) -> bool:
    """Fila 4: score 30–75 Y agente no confirma (None o False)."""
    score = entrada.score_final.score_final
    return UMBRAL_BAJO <= score <= (UMBRAL_ALTO - 1) and entrada.confirmacion_agente is not True


def _score_bajo_con_bandera(entrada: EntradaMotor) -> bool:
    """Fila 5: score < 30 Y hay bandera media o alta."""
    score = entrada.score_final.score_final
    if score >= UMBRAL_BAJO:
        return False
    # Bandera media o alta en cabeceras
    for b in entrada.banderas_cabeceras:
        if b.severidad in ("media", "alta"):
            return True
    # Bandera media o alta en adjuntos
    for adj in entrada.resultado_adjuntos:
        for b in adj.banderas:
            if b.severidad in ("media", "alta"):
                return True
    # Bandera media o alta en VT
    for vt in entrada.resultados_vt:
        for b in vt.banderas:
            if b.severidad in ("media", "alta"):
                return True
    return False


def _score_bajo_sin_indicadores(entrada: EntradaMotor) -> bool:
    """Fila 6: score < 30 Y sin banderas medias/altas Y verificaciones completas."""
    # Si llegamos aquí, las filas 1–5 no aplicaron:
    # - No hay verificaciones incompletas (fila 1 no aplicó)
    # - Score < 76 (fila 2 no aplicó)
    # - Score no está en 30–75 con agente confirmando (fila 3 no aplicó)
    # - Score no está en 30–75 con agente no confirmando (fila 4 no aplicó)
    # - Score < 30 sin bandera media/alta (fila 5 no aplicó)
    # → score < 30, sin banderas, verificaciones completas
    return True


# --- Tabla de decisión (6 filas, research D4) ---


def evaluar_tabla(
    entrada: EntradaMotor,
) -> tuple[Veredicto, NivelSeveridad, Ruta]:
    """Evalúa la tabla de decisión; retorna (veredicto, severidad, ruta).

    Se evalúan las 6 filas en orden; la primera que aplica produce
    el resultado. Por construcción, la fila 6 siempre aplica (catch-all).
    """
    predicados = [
        _hay_verificacion_incompleta,
        _score_alto,
        _score_medio_agente_confirma,
        _score_medio_agente_no_confirma,
        _score_bajo_con_bandera,
        _score_bajo_sin_indicadores,
    ]
    resultados: list[tuple[Veredicto, NivelSeveridad, Ruta]] = [
        ("revision_manual", "Medio", "heuristica"),
        ("malicioso", "Alto", "heuristica"),
        ("malicioso", "Alto", "ia"),
        ("sospechoso", "Medio", "heuristica"),
        ("sospechoso", "Medio", "heuristica"),
        ("sin_indicadores", "Bajo", "heuristica"),
    ]
    for predicado, resultado in zip(predicados, resultados):
        if predicado(entrada):
            return resultado
    # Por construcción, la fila 6 siempre aplica (catch-all).
    # Llegar aquí es un error de lógica — la fila 6 retorna True incondicionalmente.
    raise RuntimeError("tabla de decisión: ninguna fila aplicó (bug interno)")
