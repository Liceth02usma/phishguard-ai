"""Siembra de datos deterministas (spec 011, M14, FR-006).

Genera exactamente 100 análisis por fórmula sin aleatoriedad:
- 55 sin_indicadores, 15 sospechoso, 30 malicioso
- 60 por heurística, 40 con IA
- Fechas distribuidas en los últimos 90 días en America/Bogota
- Idempotente: borra siembra previa antes de insertar
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytz

from .modelos import (
    AnalisisPersistido,
    RETENCION_ANALISIS_DIAS,
    SIEMBRA_MALICIOSOS,
    SIEMBRA_SIN_INDICADORES,
    SIEMBRA_SIN_MODELO,
    SIEMBRA_SOSPECHOSOS,
    SIEMBRA_TOTAL,
    ZONA_HORARIA,
)
from .repositorio import RepositorioAnalisis


def sembrar_datos(
    *,
    repo: RepositorioAnalisis,
    ahora: datetime | None = None,
) -> int:
    """Genera 100 análisis deterministas y los persiste (FR-006).

    Idempotente: borra siembra previa antes de insertar (I4).
    Retorna: número de documentos insertados (100).
    """
    ts = ahora or datetime.now(tz=timezone.utc)
    tz_obj = pytz.timezone(ZONA_HORARIA)

    # 1. Borrar siembra previa (idempotencia)
    previos = repo.listar({"origen": "siembra"})
    for doc in previos:
        msg_id = doc.get("message_id", "")
        if msg_id:
            repo.borrar(msg_id)

    # 2. Generar 100 análisis por fórmula
    analisis = _generar_analisis_siembra(ts, tz_obj)

    # 3. Persistir
    for a in analisis:
        repo.guardar(a.model_dump(mode="json"))

    return SIEMBRA_TOTAL


def _generar_analisis_siembra(
    ahora: datetime,
    tz_obj: timezone,
) -> list[AnalisisPersistido]:
    """Genera 100 AnalisisPersistido deterministas."""
    # Distribución de veredictos: 55 sin_ind + 15 sos + 30 mal
    veredictos: list[str] = (
        ["sin_indicadores"] * SIEMBRA_SIN_INDICADORES
        + ["sospechoso"] * SIEMBRA_SOSPECHOSOS
        + ["malicioso"] * SIEMBRA_MALICIOSOS
    )

    # Distribución de rutas: 60 heurística + 40 ia
    # Los primeros 60 van por heurística, los últimos 40 por IA
    rutas: list[str] = (
        ["heuristica"] * SIEMBRA_SIN_MODELO
        + ["ia"] * (SIEMBRA_TOTAL - SIEMBRA_SIN_MODELO)
    )

    # Severidad por veredicto
    severidad_map: dict[str, str] = {
        "sin_indicadores": "Bajo",
        "sospechoso": "Medio",
        "malicioso": "Alto",
    }

    # Banderas por veredicto
    banderas_map: dict[str, list[str]] = {
        "sin_indicadores": [],
        "sospechoso": ["CAB_SPF_FAIL", "URL_ACORTADOR"],
        "malicioso": ["CAB_SPF_FAIL", "CAB_DKIM_FAIL", "ADJ_MACRO"],
    }

    # Fechas distribuidas en los últimos 90 días
    # Fórmula: día = ahora - (90 - i) días, para i en 0..99
    # Esto distribuye 100 análisis en 90 días (algunos días tienen 2)
    resultado: list[AnalisisPersistido] = []
    for i in range(SIEMBRA_TOTAL):
        dias_atras = RETENCION_ANALISIS_DIAS - i
        fecha = ahora - timedelta(days=dias_atras)

        veredicto = veredictos[i]
        ruta = rutas[i]
        severidad = severidad_map[veredicto]
        banderas = banderas_map[veredicto]

        # Score por veredicto (determinista)
        score_map: dict[str, int] = {
            "sin_indicadores": 10,
            "sospechoso": 50,
            "malicioso": 85,
        }

        expira_en = fecha + timedelta(days=RETENCION_ANALISIS_DIAS)

        resultado.append(
            AnalisisPersistido(
                message_id=f"siembra_{i + 1:03d}",
                origen="siembra",
                modo="produccion",
                fecha=fecha,
                duracion_ms=250 if ruta == "heuristica" else 1500,
                correo_enmascarado={
                    "remitente": "s***@siembra.test",
                    "asunto": f"Correo siembra #{i + 1}",
                },
                score_final=score_map[veredicto],
                ruta=ruta,  # type: ignore[arg-type]
                veredicto=veredicto,  # type: ignore[arg-type]
                nivel_severidad=severidad,  # type: ignore[arg-type]
                banderas=banderas,
                reglas_aplicadas=["R1"] if veredicto == "malicioso" and ruta == "reglas" else [],
                autenticacion={"spf": "fail"} if veredicto != "sin_indicadores" else {},
                urls=["http://evil.com/login"] if veredicto == "malicioso" else [],
                adjuntos_nombres=["doc.docm"] if veredicto == "malicioso" else [],
                version_pesos="v1",
                version_modelo="gemini-2.5-flash-lite",
                consultas_vt=1 if veredicto == "malicioso" else 0,
                aciertos_cache_vt=0,
                expira_en=expira_en,
            )
        )

    return resultado
