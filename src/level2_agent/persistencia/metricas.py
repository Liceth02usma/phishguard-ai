"""Cálculo de métricas sobre análisis (spec 011, M14, FR-004).

Función pura: cero I/O, cero estado, cero aleatoriedad.
Recibe lista de AnalisisPersistido, retorna Metricas.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

import pytz

from .modelos import (
    AnalisisPersistido,
    Metricas,
    PorDia,
    ZONA_HORARIA,
)


def calcular_metricas(
    analisis: list[AnalisisPersistido],
    *,
    tz: str = ZONA_HORARIA,
    inicio: date | None = None,
    fin: date | None = None,
) -> Metricas:
    """Calcula métricas sobre una lista de análisis (función pura).

    Invariante I3: por_dia tiene un elemento por cada día del rango.
    Invariante I5: tasa_falsos_positivos es None si no hay retroalimentación.
    """
    total = len(analisis)

    # --- por_veredicto ---
    conteo_veredicto: Counter[str] = Counter()
    for a in analisis:
        conteo_veredicto[a.veredicto] += 1
    por_veredicto = dict(conteo_veredicto)

    # --- pct_sin_modelo ---
    sin_modelo = sum(
        1 for a in analisis if a.ruta in ("reglas", "heuristica")
    )
    pct_sin_modelo = (sin_modelo / total * 100) if total > 0 else 0.0

    # --- duracion_media_ms ---
    if total > 0:
        duracion_total = sum(a.duracion_ms for a in analisis)
        duracion_media_ms = duracion_total / total
    else:
        duracion_media_ms = 0.0

    # --- por_dia ---
    por_dia = _calcular_por_dia(analisis, tz=tz, inicio=inicio, fin=fin)

    # --- indicadores_frecuentes ---
    contador_ind: Counter[str] = Counter()
    for a in analisis:
        for b in a.banderas:
            contador_ind[b] += 1
        for r in a.reglas_aplicadas:
            contador_ind[r] += 1
    indicadores_frecuentes = contador_ind.most_common(10)

    # --- tasa_falsos_positivos ---
    con_retro = [
        a for a in analisis if a.retroalimentacion is not None
    ]
    if con_retro:
        fp = sum(
            1
            for a in con_retro
            if a.retroalimentacion == "falso_positivo"
        )
        tasa_falsos_positivos = fp / len(con_retro) * 100
    else:
        tasa_falsos_positivos = None

    # --- consultas_vt y aciertos_cache ---
    consultas_vt = sum(a.consultas_vt for a in analisis)
    aciertos_cache = sum(a.aciertos_cache_vt for a in analisis)

    return Metricas(
        total=total,
        por_veredicto=por_veredicto,
        pct_sin_modelo=round(pct_sin_modelo, 2),
        duracion_media_ms=round(duracion_media_ms, 2),
        por_dia=por_dia,
        indicadores_frecuentes=indicadores_frecuentes,
        tasa_falsos_positivos=(
            round(tasa_falsos_positivos, 2)
            if tasa_falsos_positivos is not None
            else None
        ),
        consultas_vt=consultas_vt,
        aciertos_cache=aciertos_cache,
    )


def _calcular_por_dia(
    analisis: list[AnalisisPersistido],
    *,
    tz: str,
    inicio: date | None,
    fin: date | None,
) -> list[PorDia]:
    """Calcula desglose por día con relleno de ceros (I3)."""
    tz_obj = pytz.timezone(tz)

    # Convertir fechas UTC a fecha local
    dias_docs: Counter[date] = Counter()
    dias_veredicto: dict[date, Counter[str]] = {}

    for a in analisis:
        local_dt = a.fecha.astimezone(tz_obj)
        d = local_dt.date()
        dias_docs[d] += 1
        if d not in dias_veredicto:
            dias_veredicto[d] = Counter()
        dias_veredicto[d][a.veredicto] += 1

    # Determinar rango
    if analisis:
        fechas_docs = sorted(dias_docs.keys())
        min_fecha = inicio or fechas_docs[0]
        max_fecha = fin or fechas_docs[-1]
    else:
        if inicio and fin:
            min_fecha = inicio
            max_fecha = fin
        else:
            return []

    # Generar todos los días del rango (incluidos cero)
    resultado: list[PorDia] = []
    current = min_fecha
    while current <= max_fecha:
        c = dias_veredicto.get(current, Counter())
        resultado.append(
            PorDia(
                fecha=current,
                total=dias_docs.get(current, 0),
                malicioso=c.get("malicioso", 0),
                sospechoso=c.get("sospechoso", 0),
                revision_manual=c.get("revision_manual", 0),
                sin_indicadores=c.get("sin_indicadores", 0),
            )
        )
        current += timedelta(days=1)

    return resultado
