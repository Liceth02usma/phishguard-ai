"""Router de integraciones: GET /api/integraciones (spec 012).

AC-API-06: nunca revela claves ni URLs internas.
"""

from __future__ import annotations

import os

from fastapi import APIRouter
from src.api.deps import APIKeyDep

router = APIRouter(prefix="/integraciones", tags=["Integraciones"])


@router.get("")
async def get_integraciones(_: APIKeyDep) -> dict[str, object]:
    """Estado de Mongo, VT, modelo y Gmail (sin claves)."""
    # Mongo
    mongo_uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
    mongo_estado = "ok" if mongo_uri else "error"

    # VirusTotal
    vt_key = os.environ.get("VT_API_KEY", "")
    vt_estado = "ok" if vt_key else "degradado"
    vt_modo = "public" if not os.environ.get("VT_TIER", "") else os.environ.get("VT_TIER", "public")

    # Modelo (Gemini)
    gemini_key = os.environ.get("GOOGLE_API_KEY", "")
    modelo_estado = "ok" if gemini_key else "error"

    # Gmail
    gmail_creds = os.path.exists("credenciales.json") or os.path.exists("token.json")
    gmail_estado = "ok" if gmail_creds else "degradado"

    return {
        "mongo": {"estado": mongo_estado},
        "virustotal": {
            "estado": vt_estado,
            "modo": vt_modo,
        },
        "modelo": {"estado": modelo_estado},
        "gmail": {"estado": gmail_estado},
    }
