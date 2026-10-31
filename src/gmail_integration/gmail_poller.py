"""Gmail Poller — ciclo de polling que analiza correos y ejecuta acciones.

Flujo por correo:
1. Lee raw de Gmail → normaliza (spec 002)
2. analyze_email() → PhishingReport con veredicto (specs 003–009)
3. ejecutar_acciones() → acciones según tabla veredicto→acciones (spec 010)
   - Gmail: etiquetar, archivar, marcar leído
   - Jira: crear ticket (notificación al SOC)
4. guardar_analisis() → persistencia en MongoDB (spec 011)

DRY_RUN activo por defecto (ACCIONES_DRY_RUN=true, Art. V.2).
Para producción: ACCIONES_DRY_RUN=false + credenciales Jira configuradas.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

from src.gmail_integration.gmail_auth import authenticate_gmail
from src.gmail_integration.gmail_reader import (
    get_gmail_service,
    get_message_raw,
    list_unread_messages,
)
from src.level2_agent.agent import analyze_email
from src.level2_agent.normalizacion import normalizar_desde_gmail

POLL_INTERVAL = 30


def _extraer_remitente(email_data: object) -> str:
    """Extrae la dirección del remitente desde las cabeceras."""
    import json

    try:
        headers = json.loads(email_data.headers) if email_data.headers else {}  # type: ignore[union-attr]
        sender = headers.get("From", "")
        if "<" in sender and ">" in sender:
            return sender.split("<")[1].split(">")[0].strip()
        return sender.strip()
    except (json.JSONDecodeError, IndexError, AttributeError):
        return ""


def process_message(service: Any, msg_id: str) -> None:
    try:
        t0 = time.monotonic()
        raw_bytes = get_message_raw(service, msg_id)
        email_data = normalizar_desde_gmail(raw_bytes, msg_id)
        logger.info("Analizando correo: %s", email_data.subject)
        report = analyze_email(email_data)
        duracion_ms = int((time.monotonic() - t0) * 1000)

        # --- Ejecutar acciones según veredicto (spec 010) ---
        try:
            from src.level2_agent.acciones import (
                EntradaAcciones,
                ejecutar_acciones,
            )
            from src.level2_agent.acciones.gmail_adapter import GmailReal
            from src.level2_agent.acciones.jira_adapter import JiraReal

            entrada_acciones = EntradaAcciones(
                veredicto=report.veredicto,  # type: ignore[arg-type]
                nivel_severidad=report.nivel_severidad,  # type: ignore[arg-type]
                message_id=msg_id,
                remitente=_extraer_remitente(email_data),
                asunto=email_data.subject,
                urls=list(email_data.urls),
                reporte=report,
                origen="gmail",
            )
            gmail_adapter = GmailReal(service)
            jira_adapter = JiraReal()

            resultado_acciones = ejecutar_acciones(
                entrada_acciones,
                gmail=gmail_adapter,
                jira=jira_adapter,
            )

            # Log de acciones ejecutadas
            for ra in resultado_acciones.acciones:
                if ra.ejecutada:
                    logger.info(
                        "Acción ejecutada: %s → %s (motivo: %s)",
                        ra.accion.value,
                        ra.destino,
                        ra.motivo,
                    )
                else:
                    logger.info(
                        "Acción simulada/omitida: %s → %s (motivo: %s)",
                        ra.accion.value,
                        ra.destino,
                        ra.motivo,
                    )

            if resultado_acciones.ticket_key:
                logger.info(
                    "Ticket Jira: %s (huella: %s)",
                    resultado_acciones.ticket_key,
                    resultado_acciones.huella_campaña,
                )

        except Exception as e:
            logger.warning("Error en ejecutor de acciones %s: %s", msg_id, e)
            # Fallback: si falla el ejecutor, al menos etiquetar/marcar
            if report.es_phishing:
                from src.gmail_integration.gmail_reader import move_to_label
                move_to_label(service, msg_id, "Phishing Alertas")
            else:
                from src.gmail_integration.gmail_reader import mark_as_read
                mark_as_read(service, msg_id)

        # --- Persistencia del análisis (spec 011) ---
        try:
            from src.level2_agent.persistencia import guardar_analisis
            from src.level2_agent.agent import construir_analisis_persistido

            analisis = construir_analisis_persistido(
                email_data,
                report,
                message_id=msg_id,
                duracion_ms=duracion_ms,
                score_final=int(report.score_clasificador or 0),
                veredicto=report.veredicto,
                nivel_severidad=report.nivel_severidad,
                version_modelo=report.version_modelo or "indeterminada",
            )
            guardar_analisis(analisis)
        except Exception as e:
            logger.warning("No se pudo persistir análisis %s: %s", msg_id, e)

    except Exception as e:
        logger.error("Error procesando mensaje %s: %s", msg_id, e)


def poll_loop():
    logger.info("Iniciando Gmail Poller...")
    creds = authenticate_gmail()
    service = get_gmail_service(creds)
    logger.info("Conectado a Gmail. Revisando cada %s segundos...", POLL_INTERVAL)

    while True:
        try:
            msg_ids = list_unread_messages(service, max_results=5)
            if msg_ids:
                logger.info("Encontrados %s correos nuevos", len(msg_ids))
                for msg_id in msg_ids:
                    process_message(service, msg_id)
            else:
                logger.debug("Sin correos nuevos")
        except Exception as e:
            logger.error("Error en ciclo de polling: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll_loop()
