"""Router de muestras: GET /api/samples (spec 012).

Lee fixtures de tests/fixtures/*.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from src.api.deps import APIKeyDep
from src.api.schemas.analisis import MuestraResponse

router = APIRouter(prefix="/samples", tags=["Muestras"])

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"


@router.get("", response_model=list[MuestraResponse])
async def get_samples(_: APIKeyDep) -> list[MuestraResponse]:
    """Casos de ejemplo precargados para el modo muestra."""
    muestras: list[MuestraResponse] = []

    if _FIXTURES_DIR.is_dir():
        for f in sorted(_FIXTURES_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                muestras.append(
                    MuestraResponse(
                        id=f.stem,
                        nombre=data.get("subject", f.stem)[:80],
                        descripcion=f"Fixture: {f.stem}",
                        contenido=json.dumps(data, ensure_ascii=False)[:2000],
                    )
                )
            except Exception:
                continue

    if not muestras:
        # Fallback si no hay fixtures
        muestras = [
            MuestraResponse(
                id="benign",
                nombre="Correo legítimo",
                descripcion="Newsletter benigna de ejemplo",
                contenido="De: news@empresa.com\nSubject: Tu boletín semanal\n\nHola...",
            ),
            MuestraResponse(
                id="malicious",
                nombre="Phishing de banca",
                descripcion="Suplantación de banco",
                contenido="De: soporte@banc0-seguro.com\nSubject: Acceso bloqueado\n\n...",
            ),
        ]

    return muestras
