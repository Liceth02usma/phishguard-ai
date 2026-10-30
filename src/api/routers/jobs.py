"""Router de jobs: GET/POST /api/jobs/gmail (spec 012)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from src.api.deps import APIKeyDep

router = APIRouter(prefix="/jobs/gmail", tags=["Jobs"])


@router.get("")
async def get_jobs_gmail(_: APIKeyDep) -> dict[str, object]:
    """Estado del poller."""
    return {
        "ultimo_ciclo": None,
        "pendientes": 0,
        "fallidos": 0,
    }


@router.post("/run")
async def post_jobs_gmail_run(_: APIKeyDep) -> dict[str, object]:
    """Forzar un ciclo del poller (Art. V.8: sin roles)."""
    # TODO: invocar poller en background
    return {
        "ultimo_ciclo": datetime.now(tz=timezone.utc).isoformat(),
        "pendientes": 0,
        "fallidos": 0,
    }
