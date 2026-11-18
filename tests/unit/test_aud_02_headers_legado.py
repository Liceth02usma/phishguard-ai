"""Auditoría AUD-02 (defecto ALTO, CORREGIDO 2026-11-17): `headers` legado.

Historia: `normalizacion._headers_legado` retornaba `str(dict)` (repr de
Python con comillas simples) en lugar de `json.dumps`. Todo consumidor que
usaba `json.loads(email_data.headers)` fallaba y degradaba en silencio:

- `gmail_poller._extraer_remitente` → "" siempre → la huella de campaña
  (spec 010) se calculaba sin remitente y los tickets Jira no lo mostraban.
- `agent._extraer_dominio_remitente` → "" siempre → la consulta VT del
  dominio del remitente NUNCA se ejecutaba (agent.py: `if dominio:`).
- `genetic_logic._parsear_headers` → no encontraba claves → los genes
  derivados de cabeceras (from/date/received/...) perdían su entrada.

Fix aplicado: `_headers_legado` usa `json.dumps` + los consumidores hacen
búsqueda case-insensitive (las claves van en minúsculas). Estas pruebas son
ahora guardias de regresión.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def _email_data(fabrica_eml: Callable[..., bytes]) -> Any:
    from src.level2_agent.normalizacion import normalizar_desde_gmail

    eml = fabrica_eml(texto="cuerpo de prueba", remitente="juan.perez@empresa.com")
    return normalizar_desde_gmail(eml, "msg-aud-02")


def test_headers_legado_es_json_valido(fabrica_eml) -> None:  # type: ignore[no-untyped-def]
    """`email_data.headers` debe ser JSON parseable con la clave 'from'."""
    ed = _email_data(fabrica_eml)
    parsed = json.loads(ed.headers)
    assert "from" in parsed


def test_poller_extrae_remitente(fabrica_eml) -> None:  # type: ignore[no-untyped-def]
    """El poller debe extraer la dirección del remitente desde headers."""
    from src.gmail_integration.gmail_poller import _extraer_remitente

    ed = _email_data(fabrica_eml)
    assert _extraer_remitente(ed) == "juan.perez@empresa.com"


def test_agent_dominio_remitente(fabrica_eml) -> None:  # type: ignore[no-untyped-def]
    """`_extraer_dominio_remitente` debe devolver el dominio del remitente."""
    from src.level2_agent.agent import _extraer_dominio_remitente

    ed = _email_data(fabrica_eml)
    assert _extraer_dominio_remitente(ed) == "empresa.com"


def test_genetico_parsea_from(fabrica_eml) -> None:  # type: ignore[no-untyped-def]
    """La lógica genética debe leer el remitente desde headers."""
    from src.level3_logic.genetic_logic import _parsear_headers

    ed = _email_data(fabrica_eml)
    parsed = _parsear_headers(ed.headers)
    assert "from" in parsed, parsed
    assert "juan.perez@empresa.com" in parsed["from"]


def test_headers_conserva_valores_caracterizacion(fabrica_eml) -> None:  # type: ignore[no-untyped-def]
    """Caracterización: los valores SÍ están presentes (solo el formato falla)."""
    ed = _email_data(fabrica_eml)
    assert "juan.perez@empresa.com" in ed.headers
    assert "destino@empresa.com" in ed.headers
