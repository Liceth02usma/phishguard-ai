"""Router de jobs: GET/POST /api/jobs/gmail (spec 012)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks
from src.api.deps import APIKeyDep

router = APIRouter(prefix="/jobs/gmail", tags=["Jobs"])
logger = logging.getLogger(__name__)


def _run_ciclo_gmail() -> None:
    """Ejecuta un ciclo único de polling de Gmail en background.

    Requiere token.json en la raíz (creado por el primer arranque del poller).
    Falla silenciosamente si las credenciales no están disponibles.
    """
    try:
        from src.gmail_integration.gmail_auth import authenticate_gmail
        from src.gmail_integration.gmail_poller import process_message
        from src.gmail_integration.gmail_reader import (
            get_gmail_service,
            list_unread_messages,
        )

        creds = authenticate_gmail()
        service = get_gmail_service(creds)
        msg_ids = list_unread_messages(service, max_results=5)
        logger.info("Ciclo manual: %s correos encontrados", len(msg_ids))
        for msg_id in msg_ids:
            process_message(service, msg_id)
    except Exception as exc:
        logger.warning("Ciclo de polling fallido: %s", exc)


@router.get("")
async def get_jobs_gmail(_: APIKeyDep) -> dict[str, object]:
    """Estado del poller."""
    return {
        "ultimo_ciclo": None,
        "pendientes": 0,
        "fallidos": 0,
    }


@router.post("/run")
async def post_jobs_gmail_run(
    _: APIKeyDep,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    """Forzar un ciclo del poller en background (Art. V.8: sin roles)."""
    background_tasks.add_task(_run_ciclo_gmail)
    return {
        "estado": "iniciado",
        "ultimo_ciclo": datetime.now(tz=UTC).isoformat(),
        "pendientes": 0,
        "fallidos": 0,
    }
