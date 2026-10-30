"""Router de salud: GET /api/health (spec 012).

Único endpoint sin autenticación.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Salud"])


@router.get("/health")
async def get_health() -> dict[str, str]:
    """Estado del servicio (sin X-API-Key)."""
    # TODO: verificar Mongo ping cuando esté disponible
    return {"estado": "ok"}
