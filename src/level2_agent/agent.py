"""Pipeline principal de análisis de phishing (wire-up end-to-end).

Flujo:
1. Score genético (spec 007) → score_final
   - Internamente: banderas (003) + URLs (004) + adjuntos (005)
2. Si score < 30 → ruta benigna (sin agente)
3. Si score > 75 → ruta maliciosa (sin agente)
4. Si 30–75 → agente IA sin estado (spec 009) → motor de decisión (spec 008)
5. Veredicto final → PhishingReport

Wire-up (specs 003/004/005/006/007/008/009):
- evaluar_banderas (003) para evidencia al motor de decisión
- VirusTotal (006) para URLs/dominios del correo
- EntradaMotor completa con banderas, VT, verificaciones_incompletas
"""

import logging

from dotenv import load_dotenv

from .models import (
    SCORE_FALLBACK,
    SCORE_UMBRAL_ALTO,
    SCORE_UMBRAL_BAJO,
    SEVERIDAD_ALTO,
    SEVERIDAD_BAJO,
    SEVERIDAD_CRITICO,
    SEVERIDAD_MEDIO,
    EmailData,
    PhishingReport,
)
from .normalizacion import enmascarar_para_terceros

load_dotenv()
logger = logging.getLogger(__name__)


def _genetic_score(
    email_data: EmailData,
    adjuntos_analizados: tuple[object, ...] = (),
) -> dict:
    """Calcula el score final usando el clasificador lineal + banderas (spec 007)."""
    try:
        from src.level3_logic.scoring import calcular_score_final

        resultado = calcular_score_final(
            email_data, adjuntos_analizados=adjuntos_analizados
        )
        return {
            "score": resultado.score_final,
            "score_clasificador": resultado.score_clasificador,
            "genes_implicados": [
                {"caracteristica": g.caracteristica, "peso": g.peso}
                for g in resultado.genes_implicados
            ],
            "version_modelo": resultado.version_modelo,
            "puntos_banderas": resultado.puntos_banderas,
            "score_final_obj": resultado,
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


def _extraer_dominio_remitente(email_data: EmailData) -> str:
    """Extrae el dominio del remitente desde las cabeceras del correo."""
    import json

    try:
        headers = json.loads(email_data.headers) if email_data.headers else {}
        sender = headers.get("From", "")
        if "@" in sender:
            # Extraer solo el email entre < > si existe
            if "<" in sender and ">" in sender:
                sender = sender.split("<")[1].split(">")[0]
            return sender.split("@")[-1].strip()
    except (json.JSONDecodeError, IndexError):
        pass
    return ""


def _consultar_vt(email_data: EmailData) -> tuple[list[object], list[object]]:
    """Consulta VirusTotal para URLs y dominio del remitente (spec 006).

    Returns:
        (resultados_vt, verificaciones_incompletas)
    """
    resultados_vt: list[object] = []
    verificaciones_incompletas: list[object] = []

    try:
        from src.level2_agent.virustotal import consultar_url, consultar_dominio
        from src.level2_agent.decision.modelos import VerificacionIncompleta

        # Consultar URLs del correo
        for url in email_data.urls[:10]:  # Presupuesto: máx 10 URLs
            try:
                resultado = consultar_url(url)
                resultados_vt.append(resultado)
            except Exception as exc:
                logger.warning("VT URL degradada (%s): %s", url, exc)
                verificaciones_incompletas.append(
                    VerificacionIncompleta(
                        tipo="vt_url",
                        razon=f"VT_NO_DISPONIBLE: {exc}",
                    )
                )

        # Consultar dominio del remitente (extraído de cabeceras)
        dominio = _extraer_dominio_remitente(email_data)
        if dominio:
                try:
                    resultado = consultar_dominio(dominio)
                    resultados_vt.append(resultado)
                except Exception as exc:
                    logger.warning("VT dominio degradado (%s): %s", dominio, exc)
                    verificaciones_incompletas.append(
                        VerificacionIncompleta(
                            tipo="vt_dominio",
                            razon=f"VT_NO_DISPONIBLE: {exc}",
                        )
                    )

    except ImportError:
        logger.warning("VirusTotal no disponible. Verificaciones VT omitidas.")
    except Exception as e:
        logger.error("Error general VT: %s", e)

    return resultados_vt, verificaciones_incompletas


def _evaluar_banderas_cabeceras(email_data: EmailData) -> tuple[object, object]:
    """Evalúa banderas de cabeceras (spec 003) para evidencia al motor.

    Returns:
        (ResultadoBanderas | None, VerificacionIncompleta list)
    """
    verificaciones_incompletas: list[object] = []
    resultado_band = None

    try:
        from src.level2_agent.banderas import evaluar_banderas
        from src.level2_agent.banderas.configuracion import ConfigBanderas

        config_band = ConfigBanderas.desde_entorno()
        resultado_band = evaluar_banderas(email_data, config=config_band)
    except ImportError:
        logger.warning("Banderas de cabeceras no disponibles.")
    except Exception as exc:
        logger.warning("Banderas degradadas: %s", exc)

    return resultado_band, verificaciones_incompletas


def generate_benign_report(score: float) -> PhishingReport:
    return PhishingReport(
        resumen="Tráfico seguro confirmado: Notificación automatizada del sistema que clasifica el correo electrónico como mensaje legítimo.",
        analisis_tecnico=f"Evaluación inicial satisfactoria. El score de riesgo obtenido es de {score:.0f}/100, manteniéndose por debajo del umbral de sospecha ({SCORE_UMBRAL_BAJO}/100).",
        indicadores_phishing=[],
        es_phishing=False,
        nivel_severidad=SEVERIDAD_BAJO,
        justificacion_veredicto="El mensaje superó exitosamente los controles de filtrado perimetral del Algoritmo Genético. No se observaron patrones de ingeniería social, ni anomalías críticas en las firmas de autenticación técnica analizadas en las cabeceras. Se autoriza su entrega ordinaria al usuario.",
        veredicto="sin_indicadores",
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
        veredicto="malicioso",
    )


def _agente_zona_gris(
    email_data: EmailData,
    score: float,
    genes: list,
    score_clasificador: float | None,
    version_modelo: str | None,
    *,
    resultado_band: object | None = None,
    resultados_vt: list[object] | None = None,
    verificaciones_incompletas: list[object] | None = None,
) -> PhishingReport:
    """Ruta de zona gris (30–75): agente IA sin estado + motor de decisión.

    Spec 009: consultar_agente con evidencia estructurada.
    Spec 008: evaluar_veredicto para veredicto final con evidencia completa.
    """
    from src.level2_agent.agente import consultar_agente, EntradaAgente
    from src.level3_logic.scoring.modelos import ScoreFinal

    score_final_obj = ScoreFinal(
        score_final=int(score),
        score_clasificador=score_clasificador or float(score),
        puntos_banderas=0,
        version_modelo=version_modelo or "indeterminada",
    )

    # Construir entrada del agente con evidencia disponible
    entrada_agente = EntradaAgente(
        email_data=email_data,
        score_final=score_final_obj,
    )

    try:
        resultado_agente = consultar_agente(entrada_agente)
    except Exception as e:
        logger.error("Error en agente IA sin estado: %s", e)
        resultado_agente = None

    # Motor de decisión (spec 008) con evidencia completa
    try:
        from src.level2_agent.decision import evaluar_veredicto, EntradaMotor

        entrada_motor_kwargs: dict = {
            "email_data": email_data,
            "score_final": score_final_obj,
            "confirmacion_agente": (
                resultado_agente.confirmacion_agente if resultado_agente else None
            ),
        }

        # Enriquecer con banderas de cabeceras (spec 003)
        if resultado_band is not None:
            entrada_motor_kwargs["banderas_cabeceras"] = resultado_band.banderas
            entrada_motor_kwargs["estados_autenticacion"] = (
                resultado_band.estados_autenticacion
            )

        # Enriquecer con resultados VT (spec 006)
        if resultados_vt:
            entrada_motor_kwargs["resultados_vt"] = resultados_vt

        # Enriquecer con verificaciones incompletas
        if verificaciones_incompletas:
            entrada_motor_kwargs["verificaciones_incompletas"] = (
                verificaciones_incompletas
            )

        entrada_motor = EntradaMotor(**entrada_motor_kwargs)
        veredicto = evaluar_veredicto(entrada_motor)
    except ImportError:
        logger.warning("Motor de decisión no disponible. Usando heurística simple.")
        # Fallback: si el agente confirmó phishing, es malicioso
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
        report = generate_malicious_report(score, genes)
        report.veredicto = "malicioso"
        return report
    elif veredicto_str == "sospechoso":
        report = generate_malicious_report(score, genes)
        report.resumen = "⚠️ Correo sospechoso: " + report.resumen
        report.es_phishing = True
        report.nivel_severidad = SEVERIDAD_MEDIO
        report.veredicto = "sospechoso"
        return report
    elif veredicto_str == "revision_manual":
        # Requiere revisión manual — reportar como sospechoso
        report = generate_malicious_report(score, genes)
        report.resumen = (
            "⚠️ Requiere revisión manual: "
            + report.resumen
        )
        report.veredicto = "revision_manual"
        return report
    else:
        # sin_indicadores o benigno
        report = generate_benign_report(score)
        report.veredicto = "sin_indicadores"
        return report


def analyze_email(email_data: EmailData) -> PhishingReport:
    """Pipeline principal de análisis de phishing (wire-up end-to-end).

    1. Banderas de cabeceras (spec 003) → evidencia para motor
    2. Score genético (spec 007) → score_final
       - Internamente: banderas + URLs (004) + adjuntos (005)
    3. VirusTotal (spec 006) → reputación URLs/dominio
    4. Ruta benigna (< )30), maliciosa (> 75) o zona gris (30–75)
    5. Zona gris → agente IA (009) + motor de decisión (008) con evidencia completa
    6. Veredicto final → PhishingReport
    """
    # Paso 1: Banderas de cabeceras (spec 003) para evidencia al motor
    resultado_band, verif_band = _evaluar_banderas_cabeceras(email_data)

    # Paso 2: Score genético (spec 007)
    genetic_result = _genetic_score(email_data)
    score = genetic_result["score"]
    genes = genetic_result.get("genes_implicados", [])
    version_modelo = genetic_result.get("version_modelo")
    score_clasificador = genetic_result.get("score_clasificador")

    # Paso 3: VirusTotal (spec 006) para URLs y dominio
    resultados_vt, verif_vt = _consultar_vt(email_data)
    verificaciones_incompletas = list(verif_band) + list(verif_vt)

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
            email_data, score, genes, score_clasificador, version_modelo,
            resultado_band=resultado_band,
            resultados_vt=resultados_vt,
            verificaciones_incompletas=verificaciones_incompletas,
        )
        report.score_clasificador = score_clasificador
    return report


def construir_analisis_persistido(
    email_data: EmailData,
    report: PhishingReport,
    *,
    message_id: str,
    origen: str = "gmail",
    modo: str = "produccion",
    duracion_ms: int = 0,
    score_final: int = 0,
    ruta: str = "heuristica",
    veredicto: str = "sin_indicadores",
    nivel_severidad: str = "Bajo",
    banderas: list[str] | None = None,
    reglas_aplicadas: list[str] | None = None,
    version_pesos: str = "v1",
    version_modelo: str = "indeterminada",
) -> object:
    """Construye un AnalisisPersistido desde el resultado del pipeline (T027).

    Función helper para que el poller/API puedan persistir sin importar
    detalles internos del modelo.
    """
    from datetime import datetime, timedelta, timezone

    from .persistencia.modelos import AnalisisPersistido

    ahora = datetime.now(tz=timezone.utc)
    correo_enmascarado = enmascarar_para_terceros(email_data)

    return AnalisisPersistido(
        message_id=message_id,
        origen=origen,  # type: ignore[arg-type]
        modo=modo,  # type: ignore[arg-type]
        fecha=ahora,
        duracion_ms=duracion_ms,
        correo_enmascarado=correo_enmascarado.model_dump()
        if hasattr(correo_enmascarado, "model_dump")
        else correo_enmascarado,
        score_final=score_final,
        ruta=ruta,  # type: ignore[arg-type]
        veredicto=veredicto,  # type: ignore[arg-type]
        nivel_severidad=nivel_severidad,  # type: ignore[arg-type]
        banderas=banderas or [],
        reglas_aplicadas=reglas_aplicadas or [],
        urls=list(email_data.urls) if hasattr(email_data, "urls") else [],
        adjuntos_nombres=(
            [a.nombre for a in email_data.adjuntos]
            if hasattr(email_data, "adjuntos")
            else []
        ),
        version_pesos=version_pesos,
        version_modelo=version_modelo,
        expira_en=ahora + timedelta(days=90),
    )
