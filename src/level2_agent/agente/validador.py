"""Validación de salida del modelo (spec 009, M07, FR-004).

Parsea la respuesta cruda del modelo, la valida contra el esquema
SalidaAgente con Pydantic. Si falla, retorna None (el orquestador
maneja el reintento). Strip de markdown code fences.
"""

from __future__ import annotations

import json
import re

from src.level2_agent.agente.modelos import SalidaAgente


def _strip_markdown_fences(raw: str) -> str:
    """Elimina fences ```json ... ``` del output del modelo."""
    # Pattern: ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _extraer_json(raw: str) -> dict | None:
    """Intenta extraer un objeto JSON del texto."""
    # Primero intentar parse directo
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Buscar primer { ... } balanceado
    depth = 0
    start = -1
    for i, ch in enumerate(raw):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(raw[start : i + 1])
                except json.JSONDecodeError:
                    start = -1
    return None


def validar_salida(raw: str) -> SalidaAgente | None:
    """Valida la salida cruda del modelo contra el esquema SalidaAgente.

    Retorna SalidaAgente si la validación pasa, None si falla.
    No lanza excepciones — el orquestador maneja el reintento.
    """
    cleaned = _strip_markdown_fences(raw)
    data = _extraer_json(cleaned)
    if data is None:
        return None

    try:
        return SalidaAgente.model_validate(data)
    except Exception:
        return None
