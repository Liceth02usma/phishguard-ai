"""Factory de modelos LLM (Strategy pattern, spec 009, FR-008).

crear_modelo(proveedor) → ModeloLLM:
- "simulado" → SimuladoAdapter (cero red, para tests/CI)
- "gemini"   → GeminiAdapter (langchain-google-genai)
- "groq"     → GroqAdapter (langchain-openai + Groq API)

Selección por LLM_PROVEEDOR env var (default: "gemini").
"""

from __future__ import annotations

import os
from typing import Literal

ProveedorLLM = Literal["simulado", "gemini", "groq"]
"""Proveedores LLM soportados (Art. VI.2: catálogo cerrado)."""

PROVEEDOR_DEFAULT: ProveedorLLM = "gemini"
"""Proveedor por defecto cuando LLM_PROVEEDOR no está configurado."""


def crear_modelo(
    proveedor: ProveedorLLM | None = None,
    *,
    modelo: str | None = None,
) -> object:
    """Factory que selecciona el adapter de LLM (Strategy).

    Args:
        proveedor: Nombre del proveedor. Si es None, lee LLM_PROVEEDOR
            del entorno (default: "gemini").
        modelo: Nombre del modelo (override de LLM_MODELO). Solo aplica
            a GeminiAdapter y GroqAdapter.

    Returns:
        Instancia que cumple el Protocol ModeloLLM.

    Raises:
        ValueError: Proveedor desconocido.
    """
    if proveedor is None:
        proveedor_env = os.environ.get("LLM_PROVEEDOR", PROVEEDOR_DEFAULT)
        # Validar que es un proveedor conocido
        proveedores_validos: set[str] = {"simulado", "gemini", "groq"}
        if proveedor_env not in proveedores_validos:
            raise ValueError(
                f"Proveedor desconocido: '{proveedor_env}'. "
                f"Válidos: {sorted(proveedores_validos)}"
            )
        proveedor = proveedor_env  # type: ignore[assignment]

    if proveedor == "simulado":
        from src.level2_agent.agente.simulado_adapter import SimuladoAdapter

        return SimuladoAdapter()

    if proveedor == "gemini":
        from src.level2_agent.agente.gemini_adapter import GeminiAdapter

        return GeminiAdapter(modelo=modelo)

    if proveedor == "groq":
        from src.level2_agent.agente.groq_adapter import GroqAdapter

        return GroqAdapter(modelo=modelo)

    raise ValueError(f"Proveedor desconocido: '{proveedor}'")
