"""Router de muestras: GET /api/samples (spec 012).

Lee fixtures de tests/fixtures/*.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from src.api.deps import APIKeyDep
from src.api.schemas.analisis import MuestraResponse

router = APIRouter(prefix="/samples", tags=["Muestras"])

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"


def leer_fixture(muestra_id: str) -> dict[str, Any] | None:
    """Lee ``tests/fixtures/{muestra_id}.json`` y devuelve su contenido.

    Se usa en ``POST /api/analyses`` modo ``muestra``: sin esto el endpoint
    analizaba un stub vacío (asunto ``Muestra: x``, cuerpo vacío) y los tres
    escenarios salían siempre ``score=31 -> sospechoso``.

    Devuelve ``None`` si el id contiene separadores de ruta, no existe o el
    JSON no es un objeto (nunca lanza: la API degrada a ``None``).
    """
    if not muestra_id or any(c in muestra_id for c in ("/", "\\", "..", "\x00")):
        return None
    ruta = _FIXTURES_DIR / f"{muestra_id}.json"
    try:
        if not ruta.is_file():
            return None
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return datos if isinstance(datos, dict) else None


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
