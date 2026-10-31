"""Orquestador de acciones idempotentes (spec 010, M08).

ejecutar_acciones(entrada) -> ResultadoAcciones:
1. Verifica idempotencia (message_id ya procesado).
2. Si DRY_RUN activo → registra simulacro sin ejecutar.
3. Resuelve acciones desde la tabla.
4. Ejecuta cada acción via adapter.
5. Si Jira falla → registra error, continúa Gmail.
6. Registra resultado para idempotencia.
7. Retorna ResultadoAcciones.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from src.level2_agent.acciones.gmail_adapter import GmailAdapter
from src.level2_agent.acciones.huella import calcular_huella
from src.level2_agent.acciones.jira_adapter import JiraAdapter, sanear_texto_jira
from src.level2_agent.acciones.modelos import (
    DRY_RUN_DEFAULT,
    ETIQUETA_PHISHING,
    ETIQUETA_REVISAR,
    JIRA_PROYECTO,
    JIRA_TIPO_TICKET,
    MAX_CHARS_SUMMARY_JIRA,
    Accion,
    EntradaAcciones,
    Motivo,
    ResultadoAccion,
    ResultadoAcciones,
    ResultadoJira,
)
from src.level2_agent.acciones.tabla import resolver_acciones

logger = logging.getLogger(__name__)

# --- In-memory idempotencia store (fallback si no hay MongoDB) ---
_procesados: dict[str, ResultadoAcciones] = {}


def _dry_run_activo() -> bool:
    """Lee la env var ACCIONES_DRY_RUN (default true)."""
    val = os.environ.get("ACCIONES_DRY_RUN", "true" if DRY_RUN_DEFAULT else "false")
    return val.lower() in ("true", "1", "yes")


def _ya_procesado(message_id: str) -> ResultadoAcciones | None:
    """Consulta si el message_id ya fue procesado (idempotencia)."""
    # MongoDB lookup si disponible
    uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
    if uri:
        try:
            from pymongo import MongoClient

            client: object = MongoClient(uri, serverSelectionTimeoutMS=3000)  # type: ignore[import-untyped]
            db = client["phishguard"]  # type: ignore[index]
            doc = db["acciones_ejecutadas"].find_one({"message_id": message_id})
            if doc:
                return ResultadoAcciones.model_validate(doc.get("resultado", {}))
        except Exception:
            pass
    # Fallback in-memory
    return _procesados.get(message_id)


def _registrar_procesado(message_id: str, resultado: ResultadoAcciones) -> None:
    """Registra el message_id como procesado para idempotencia."""
    uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
    if uri:
        try:
            from pymongo import MongoClient

            client: object = MongoClient(uri, serverSelectionTimeoutMS=3000)  # type: ignore[import-untyped]
            db = client["phishguard"]  # type: ignore[index]
            db["acciones_ejecutadas"].update_one(
                {"message_id": message_id},
                {"$set": {"resultado": resultado.model_dump(mode="json")}},
                upsert=True,
            )
        except Exception:
            pass
    # Fallback in-memory
    _procesados[message_id] = resultado


def ejecutar_acciones(
    entrada: EntradaAcciones,
    *,
    gmail: GmailAdapter | None = None,
    jira: JiraAdapter | None = None,
    ahora: datetime | None = None,
) -> ResultadoAcciones:
    """Ejecuta acciones según veredicto (contract §1).

    1. Idempotencia: si message_id ya procesado → retorna sin ejecutar.
    2. DRY_RUN: si activo → registra simulacro sin ejecutar.
    3. Resuelve acciones desde la tabla.
    4. Ejecuta cada acción via adapter.
    5. Si Jira falla → registra error, continúa Gmail (D10).
    6. Registra resultado para idempotencia.
    7. Retorna ResultadoAcciones.
    """
    ts = ahora or datetime.now(tz=timezone.utc)
    msg_id = entrada.message_id

    # 1. Idempotencia
    previo = _ya_procesado(msg_id)
    if previo is not None:
        # Marcar todas como idempotencia
        acciones_idem = [
            ResultadoAccion(
                accion=a.accion,
                destino=a.destino,
                identificador=a.identificador,
                ejecutada=False,
                motivo="idempotencia",
                timestamp=ts,
            )
            for a in previo.acciones
        ]
        return ResultadoAcciones(
            acciones=acciones_idem,
            huella_campaña=previo.huella_campaña,
            ticket_key=previo.ticket_key,
            procesado=True,
        )

    # 2. Resolver acciones
    acciones_plan = resolver_acciones(entrada.veredicto)
    huella = calcular_huella(entrada.remitente, entrada.asunto, entrada.urls)

    # 3. DRY_RUN
    dry_run = _dry_run_activo()
    resultados: list[ResultadoAccion] = []
    ticket_key: str | None = None

    if dry_run:
        for acc in acciones_plan:
            destino: str = "gmail" if acc in (
                Accion.ETIQUETAR_PHISHING, Accion.ETIQUETAR_REVISAR,
                Accion.ARCHIVAR, Accion.MARCAR_LEIDO,
            ) else "jira"
            resultados.append(
                ResultadoAccion(
                    accion=acc,
                    destino=destino,  # type: ignore[arg-type]
                    identificador=msg_id,
                    ejecutada=False,
                    motivo="dry_run",
                    timestamp=ts,
                )
            )
        resultado = ResultadoAcciones(
            acciones=resultados,
            huella_campaña=huella,
            procesado=True,
        )
        _registrar_procesado(msg_id, resultado)
        return resultado

    # 4. Ejecutar acciones reales
    gmail_real = gmail
    jira_real = jira

    for acc in acciones_plan:
        try:
            resultado_acc = _ejecutar_accion(
                acc, entrada, gmail_real, jira_real, huella, ts
            )
            resultados.append(resultado_acc)
            if resultado_acc.detalle and resultado_acc.accion in (
                Accion.CREAR_TICKET, Accion.CREAR_TICKET_BAJA,
            ):
                ticket_key = resultado_acc.detalle
        except Exception as e:
            logger.error("Error ejecutando acción %s: %s", acc.value, e)
            destino_err = "jira" if acc in (Accion.CREAR_TICKET, Accion.CREAR_TICKET_BAJA) else "gmail"
            resultados.append(
                ResultadoAccion(
                    accion=acc,
                    destino=destino_err,  # type: ignore[arg-type]
                    identificador=msg_id,
                    ejecutada=False,
                    motivo="error_jira" if destino_err == "jira" else "error_gmail",  # type: ignore[arg-type]
                    timestamp=ts,
                    detalle=str(e),
                )
            )

    resultado = ResultadoAcciones(
        acciones=resultados,
        huella_campaña=huella,
        ticket_key=ticket_key,
        procesado=True,
    )
    _registrar_procesado(msg_id, resultado)
    return resultado


def _ejecutar_accion(
    accion: Accion,
    entrada: EntradaAcciones,
    gmail: GmailAdapter | None,
    jira: JiraAdapter | None,
    huella: str,
    ts: datetime,
) -> ResultadoAccion:
    """Ejecuta una acción individual via adapter."""
    msg_id = entrada.message_id

    if accion == Accion.ETIQUETAR_PHISHING:
        if gmail and entrada.origen == "gmail":
            gmail.etiquetar(msg_id, ETIQUETA_PHISHING)
        return ResultadoAccion(
            accion=accion, destino="gmail", identificador=msg_id,
            ejecutada=True, motivo="exito", timestamp=ts,
        )

    elif accion == Accion.ETIQUETAR_REVISAR:
        if gmail and entrada.origen == "gmail":
            gmail.etiquetar(msg_id, ETIQUETA_REVISAR)
        return ResultadoAccion(
            accion=accion, destino="gmail", identificador=msg_id,
            ejecutada=True, motivo="exito", timestamp=ts,
        )

    elif accion == Accion.ARCHIVAR:
        if gmail and entrada.origen == "gmail":
            gmail.archivar(msg_id)
        return ResultadoAccion(
            accion=accion, destino="gmail", identificador=msg_id,
            ejecutada=True, motivo="exito", timestamp=ts,
        )

    elif accion == Accion.MARCAR_LEIDO:
        if gmail and entrada.origen == "gmail":
            gmail.marcar_leido(msg_id)
        return ResultadoAccion(
            accion=accion, destino="gmail", identificador=msg_id,
            ejecutada=True, motivo="exito", timestamp=ts,
        )

    elif accion in (Accion.CREAR_TICKET, Accion.CREAR_TICKET_BAJA):
        if jira is None:
            return ResultadoAccion(
                accion=accion, destino="jira", identificador=msg_id,
                ejecutada=False, motivo="error_jira", timestamp=ts,
                detalle="Jira no configurado",
            )

        # Buscar ticket existente por huella (AC-ACT-07)
        existente = jira.buscar_por_huella(huella)
        if existente:
            # Vincular en vez de crear
            jira.vincular(msg_id, existente)
            return ResultadoAccion(
                accion=accion, destino="jira", identificador=msg_id,
                ejecutada=True, motivo="exito", timestamp=ts,
                detalle=existente,
            )

        # Generar screenshot del correo vía HCTI (D12)
        screenshot_url: str | None = None
        if entrada.html_body:
            try:
                from src.level2_agent.screenshots import generar_screenshot

                screenshot_url = generar_screenshot(entrada.html_body)
            except Exception as e:
                logger.warning("Error generando screenshot: %s", e)

        # Crear ticket nuevo
        prioridad = "High" if accion == Accion.CREAR_TICKET else "Medium"
        summary = sanear_texto_jira(
            f"[SOC] Phishing Report: {entrada.reporte.resumen}",
            max_chars=MAX_CHARS_SUMMARY_JIRA,
        )

        # Construir descripción con screenshot si está disponible
        descripcion = entrada.reporte.analisis_tecnico
        if screenshot_url:
            descripcion = (
                f"📸 Evidencia visual del correo:\n"
                f"{screenshot_url}\n\n"
                f"---\n\n"
                f"{descripcion}"
            )

        campos = {
            "fields": {
                "project": {"key": JIRA_PROYECTO},
                "issuetype": {"name": JIRA_TIPO_TICKET},
                "summary": summary,
                "priority": {"name": prioridad},
                "description": sanear_texto_jira(descripcion),
            }
        }
        res = jira.crear_ticket(campos)
        if res.exito:
            return ResultadoAccion(
                accion=accion, destino="jira", identificador=msg_id,
                ejecutada=True, motivo="exito", timestamp=ts,
                detalle=res.issue_key,
            )
        else:
            return ResultadoAccion(
                accion=accion, destino="jira", identificador=msg_id,
                ejecutada=False, motivo="error_jira", timestamp=ts,
                detalle=res.error,
            )

    else:
        raise ValueError(f"Acción no soportada: {accion}")
