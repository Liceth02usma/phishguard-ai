"""AC-API-08: CSV escapa fórmulas; 5001 resultados exporta 5000."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.api.csv_export import generar_csv
from src.api.schemas.analisis import (
    AccionResponse,
    AnalisisResponse,
    CorreoResponse,
    ResultadoResponse,
)


def _make_response(i: int) -> AnalisisResponse:
    return AnalisisResponse(
        id=f"msg_{i:04d}",
        origen="api",
        modo="pegar",
        creado_en=datetime.now(tz=timezone.utc),
        duracion_ms=100,
        correo=CorreoResponse(
            remitente="t***@test.com",
            asunto="=HYPERLINK(\"http://evil.com\")",
        ),
        resultado=ResultadoResponse(
            score=50,
            ruta="heuristica",
            es_phishing=False,
            veredicto="sin_indicadores",
            nivel_severidad="Bajo",
            resumen="Test",
        ),
        accion=AccionResponse(simulada=True),
    )


def test_csv_escapa_formula() -> None:
    """Asunto =HYPERLINK(...) se escapa con prefijo '."""
    items = [_make_response(1)]
    csv_text = generar_csv(items)
    # La celda del asunto debe tener prefijo '
    assert "'=HYPERLINK" in csv_text or "'=" in csv_text


def test_csv_bom_utf8() -> None:
    """CSV empieza con BOM UTF-8."""
    items = [_make_response(1)]
    csv_text = generar_csv(items)
    assert csv_text.startswith("\ufeff")


def test_csv_max_5000_filas() -> None:
    """5001 resultados → CSV con 5000 filas de datos (+1 header)."""
    items = [_make_response(i) for i in range(5001)]
    csv_text = generar_csv(items)
    lines = csv_text.strip().split("\n")
    # 1 header + 5000 data rows = 5001 lines
    assert len(lines) == 5001
