"""Módulo de generación de screenshots para tickets Jira (spec 010, D12).

API pública:
    generar_screenshot, HCTI_API_URL, HCTI_TIMEOUT_SEGUNDOS
"""

from __future__ import annotations

from .hcti_adapter import (
    HCTI_API_URL,
    HCTI_TIMEOUT_SEGUNDOS,
    generar_screenshot,
)

__all__ = [
    "HCTI_API_URL",
    "HCTI_TIMEOUT_SEGUNDOS",
    "generar_screenshot",
]
