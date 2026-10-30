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
    mark_as_read,
    move_to_label,
)
from src.level2_agent.agent import analyze_email
from src.level2_agent.normalizacion import normalizar_desde_gmail

POLL_INTERVAL = 30


def process_message(service: Any, msg_id: str) -> None:
    try:
        import time

        t0 = time.monotonic()
        raw_bytes = get_message_raw(service, msg_id)
        email_data = normalizar_desde_gmail(raw_bytes, msg_id)
        logger.info("Analizando correo: %s", email_data.subject)
        report = analyze_email(email_data)
        duracion_ms = int((time.monotonic() - t0) * 1000)

        if report.es_phishing:
            subject_preview = email_data.subject[:50]
            logger.info(
                "PHISHING DETECTADO - Asunto: %s | Severidad: %s | Indicadores: %s",
                subject_preview,
                report.nivel_severidad,
                ", ".join(report.indicadores_phishing[:3]),
            )
            move_to_label(service, msg_id, "Phishing Alertas")
        else:
            logger.info("SEGURO - Asunto: %s", email_data.subject[:50])
            mark_as_read(service, msg_id)

        # Persistencia del análisis (spec 011, T026)
        try:
            from src.level2_agent.persistencia import guardar_analisis
            from src.level2_agent.agent import construir_analisis_persistido

            veredicto = "malicioso" if report.es_phishing else "sin_indicadores"
            analisis = construir_analisis_persistido(
                email_data,
                report,
                message_id=msg_id,
                duracion_ms=duracion_ms,
                score_final=int(report.score_clasificador or 0),
                veredicto=veredicto,
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
