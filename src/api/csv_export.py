"""Exportación CSV con protección contra inyección de fórmulas (spec 012, FR-004).

Función pura: generar_csv(analisis) -> str.
UTF-8 con BOM. Prefijo ' en celdas peligrosas. Máximo 5000 filas.
"""

from __future__ import annotations

import csv
import io

from .config import CSV_BOM, CSV_MAX_FILAS, CSV_PREFIJOS_PELIGROSOS
from .schemas.analisis import AnalisisResponse


def _escapar_celda(valor: str) -> str:
    """Escapa celdas que empiezan con prefijo peligroso (CWE-1236).

    Si la celda empieza con =, +, - o @, se prepone '.
    """
    if valor and valor[0] in CSV_PREFIJOS_PELIGROSOS:
        return f"'{valor}"
    return valor


def generar_csv(analisis: list[AnalisisResponse]) -> str:
    """Genera CSV con BOM, escape de fórmulas y límite de filas.

    FR-004, AC-API-08:
    - UTF-8 con BOM
    - Prefijo ' en celdas que empiezan con =, +, -, @
    - Máximo 5000 filas (5001 resultados → 5000)
    """
    # Limitar filas
    filas = analisis[:CSV_MAX_FILAS]

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Cabecera
    writer.writerow([
        "id", "creado_en", "veredicto", "nivel_severidad",
        "score", "ruta", "remitente", "asunto",
    ])

    # Filas
    for a in filas:
        writer.writerow([
            _escapar_celda(str(a.id)),
            _escapar_celda(a.creado_en.isoformat()),
            _escapar_celda(a.resultado.veredicto),
            _escapar_celda(a.resultado.nivel_severidad),
            str(a.resultado.score),
            _escapar_celda(a.resultado.ruta),
            _escapar_celda(a.correo.remitente),
            _escapar_celda(a.correo.asunto),
        ])

    return CSV_BOM + output.getvalue()
