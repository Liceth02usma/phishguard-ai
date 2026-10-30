"""Pipeline principal de análisis de phishing (refactorizado spec 009).

Flujo:
1. Score genético (spec 007) → score_final
2. Si score < 30 → ruta benigna (sin agente)
3. Si score > 75 → ruta maliciosa (sin agente)
4. Si 30–75 → agente IA sin estado (spec 009) → motor de decisión (spec 008)
5. Veredicto final → PhishingReport
"""

import logging
import os

from dotenv import load_dotenv

from .models import (
    SCORE_FALLBACK,
    SCORE_UMBRAL_ALTO,
    SCORE_UMBRAL_BAJO,
    SEVERIDAD_ALTO,
    SEVERIDAD_BAJO,
    SEVERIDAD_CRITICO,
    EmailData,
    PhishingReport,
)
from .normalizacion import enmascarar_para_terceros

load_dotenv()
logger = logging.getLogger(__name__)


def _genetic_score(email_data: EmailData) -> dict:
    """Calcula el score final usando el clasificador lineal + banderas (spec 007)."""
    try:
        from src.level3_logic.scoring import calcular_score_final

        resultado = calcular_score_final(email_data)
        return {
            "score": resultado.score_final,
            "score_clasificador": resultado.score_clasificador,
            "genes_implicados": [
                {"caracteristica": g.caracteristica, "peso": g.peso}
                for g in resultado.genes_implicados
            ],
            "version_modelo": resultado.version_modelo,
            "puntos_banderas": resultado.puntos_banderas,
        }
    except ImportError:
        logger.warning(
            "level3_logic.scoring no disponible. Usando score fallback=%s",
            SCORE_FALLBACK,
        )
        return {
            "score": SCORE_FALLBACK,
            "genes_implicados": [],
            "version_modelo": "indeterminada",
        }
    except Exception as e:
        logger.error(
            "Error en scoring: %s. Usando score fallback=%s", e, SCORE_FALLBACK
        )
        return {
            "score": SCORE_FALLBACK,
            "genes_implicados": [],
            "version_modelo": "indeterminada",
        }


def generate_benign_report(score: float) -> PhishingReport:
    return PhishingReport(
        resumen="Tráfico seguro confirmado: Notificación automatizada del sistema que clasifica el correo electrónico como mensaje legítimo.",
        analisis_tecnico=f"Evaluación inicial satisfactoria. El score de riesgo obtenido es de {score:.0f}/100, manteniéndose por debajo del umbral de sospecha ({SCORE_UMBRAL_BAJO}/100).",
        indicadores_phishing=[],
        es_phishing=False,
        nivel_severidad=SEVERIDAD_BAJO,
        justificacion_veredicto="El mensaje superó exitosamente los controles de filtrado perimetral del Algoritmo Genético. No se observaron patrones de ingeniería social, ni anomalías críticas en las firmas de autenticación técnica analizadas en las cabeceras. Se autoriza su entrega ordinaria al usuario.",
    )


def generate_malicious_report(score: float, genes: list) -> PhishingReport:
    formato_evidencia = "\n".join(
        f"- Indicador activado: {g.get('caracteristica', g)}" for g in genes
    )
    severidad = SEVERIDAD_CRITICO if score >= 90 else SEVERIDAD_ALTO

    return PhishingReport(
        resumen="Alerta perimetral automática: El correo electrónico ha sido interceptado y clasificado directamente como amenaza debido a un índice de riesgo crítico.",
        analisis_tecnico=f"Análisis algorítmico completado. El correo electrónico arrojó un score acumulado de {score:.0f}/100, superando el umbral de seguridad tolerado ({SCORE_UMBRAL_ALTO}/100).",
        es_phishing=True,
        indicadores_phishing=[g.get("caracteristica", str(g)) for g in genes],
        nivel_severidad=severidad,
        justificacion_veredicto=f"Bloqueo automatizado preventivo por el pipeline del SOC.\n\nLa optimización polinomial basada en Algoritmos Genéticos determinó que la concurrencia de los siguientes factores representa un peligro inminente de fraude o fuga de credenciales:\n\n{formato_evidencia}\n\nEl mensaje ha sido desviado de la bandeja del usuario de forma inmediata como medida de mitigación.",
    )


def _agente_zona_gris(
    email_data: EmailData,
    score: float,
    genes: list,
    score_clasificador: float | None,
    version_modelo: str | None,
) -> PhishingReport:
    """Ruta de zona gris (30–75): agente IA sin estado + motor de decisión.

    Spec 009: consultar_agente con evidencia estructurada.
    Spec 008: evaluar_veredicto para veredicto final.
    """
    from src.level2_agent.agente import consultar_agente, EntradaAgente
    from src.level3_logic.scoring.modelos import ScoreFinal

    # Construir entrada del agente con evidencia disponible
    entrada_agente = EntradaAgente(
        email_data=email_data,
        score_final=ScoreFinal(
            score_final=int(score),
            score_clasificador=score_clasificador or float(score),
            puntos_banderas=0,
            version_modelo=version_modelo or "indeterminada",
        ),
    )

    try:
        resultado_agente = consultar_agente(entrada_agente)
    except Exception as e:
        logger.error("Error en agente IA sin estado: %s", e)
        resultado_agente = None

    # Motor de decisión (spec 008)
    try:
        from src.level2_agent.decision import evaluar_veredicto, EntradaMotor

        entrada_motor = EntradaMotor(
            email_data=email_data,
            score_final=ScoreFinal(
                score_final=int(score),
                score_clasificador=score_clasificador or float(score),
                puntos_banderas=0,
                version_modelo=version_modelo or "indeterminada",
            ),
            confirmacion_agente=(
                resultado_agente.confirmacion_agente if resultado_agente else None
            ),
        )
        veredicto = evaluar_veredicto(entrada_motor)
    except ImportError:
        logger.warning("Motor de decisión no disponible. Usando heurística simple.")
        # Fallback: si el agente confirmó phishing, es malicioso
        es_ph = (
            resultado_agente.confirmacion_agente
            if resultado_agente and resultado_agente.confirmacion_agente is not None
            else score > 50
        )
        veredicto = None  # type: ignore[assignment]
    except Exception as e:
        logger.error("Error en motor de decisión: %s", e)
        veredicto = None  # type: ignore[assignment]

    # Generar reporte basado en veredicto
    if veredicto is not None:
        return _veredicto_a_report(veredicto.veredicto, score, genes, resultado_agente)
    else:
        # Fallback sin motor de decisión
        es_ph = (
            resultado_agente.confirmacion_agente
            if resultado_agente and resultado_agente.confirmacion_agente is not None
            else score > 50
        )
        if es_ph:
            return generate_malicious_report(score, genes)
        else:
            return generate_benign_report(score)


def _veredicto_a_report(
    veredicto_str: str,
    score: float,
    genes: list,
    resultado_agente: object | None,
) -> PhishingReport:
    """Convierte el veredicto del motor de decisión a un PhishingReport."""
    if veredicto_str == "malicioso":
        return generate_malicious_report(score, genes)
    elif veredicto_str == "revision_manual":
        # Requiere revisión manual — reportar como sospechoso
        report = generate_malicious_report(score, genes)
        report.resumen = (
            "⚠️ Requiere revisión manual: "
            + report.resumen
        )
        return report
    else:
        # sin_indicadores o benigno
        return generate_benign_report(score)


def analyze_email(email_data: EmailData) -> PhishingReport:
    """Pipeline principal de análisis de phishing.

    1. Score genético (spec 007)
    2. Ruta benigna (< 30), maliciosa (> 75) o zona gris (30–75)
    3. Zona gris → agente IA sin estado (spec 009) + motor de decisión (spec 008)
    """
    genetic_result = _genetic_score(email_data)
    score = genetic_result["score"]
    genes = genetic_result.get("genes_implicados", [])
    version_modelo = genetic_result.get("version_modelo")
    score_clasificador = genetic_result.get("score_clasificador")

    if score < SCORE_UMBRAL_BAJO:
        logger.info("Score %s < %s → ruta benigna", score, SCORE_UMBRAL_BAJO)
        report = generate_benign_report(score)
        report.score_clasificador = score_clasificador
        report.version_modelo = version_modelo

    elif score > SCORE_UMBRAL_ALTO:
        logger.info("Score %s > %s → ruta maliciosa", score, SCORE_UMBRAL_ALTO)
        report = generate_malicious_report(score, genes)
        report.score_clasificador = score_clasificador
        report.version_modelo = version_modelo

    else:
        logger.info(
            "Score %s entre %s-%s → zona gris: agente IA + motor de decisión",
            score,
            SCORE_UMBRAL_BAJO,
            SCORE_UMBRAL_ALTO,
        )
        report = _agente_zona_gris(
            email_data, score, genes, score_clasificador, version_modelo
        )
        report.score_clasificador = score_clasificador
        report.version_modelo = version_modelo

    return report
