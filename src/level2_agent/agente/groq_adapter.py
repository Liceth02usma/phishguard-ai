"""Adapter del modelo Groq para el agente (spec 009, FR-008).

Implementa el Protocol ModeloLLM. Usa langchain-openai con la base URL
de Groq (API compatible con OpenAI). Se construye solo cuando se necesita
(el orquestador lo importa lazy). El modelo y temperatura son configurables
via LLM_MODELO y GROQ_API_KEY env vars.
"""

from __future__ import annotations

import os
from typing import Any

from src.level2_agent.agente.modelos import (
    LLM_TEMPERATURA,
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
"""Base URL de la API de Groq (compatible con OpenAI)."""

GROQ_MODELO_DEFAULT = "llama-3.3-70b-versatile"
"""Modelo por defecto de Groq."""


class GroqAdapter:
    """Adapter del modelo Groq que implementa ModeloLLM.

    Envuelve ChatOpenAI de langchain-openai apuntando a la API de Groq.
    Temperatura 0 para determinismo máximo.
    """

    def __init__(self, *, modelo: str | None = None) -> None:
        self._modelo_nombre = modelo or os.environ.get(
            "LLM_MODELO", GROQ_MODELO_DEFAULT
        )
        self._llm: Any = None

    def _construir_llm(self) -> Any:
        """Construye la instancia de ChatOpenAI apuntando a Groq (lazy)."""
        if self._llm is not None:
            return self._llm

        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY no configurada. "
                "Establézcala en el entorno o use LLM_PROVEEDOR=gemini."
            )

        self._llm = ChatOpenAI(
            model=self._modelo_nombre,
            api_key=api_key,
            base_url=GROQ_BASE_URL,
            temperature=LLM_TEMPERATURA,
        )
        return self._llm

    def invocar(self, prompt: str, *, herramientas: list[object] | None = None) -> str:
        """Invoca el modelo con el prompt y retorna la respuesta cruda."""
        llm = self._construir_llm()

        if herramientas:
            llm_con_herramientas = llm.bind_tools(herramientas)
            respuesta = llm_con_herramientas.invoke(prompt)
        else:
            respuesta = llm.invoke(prompt)

        # Extraer texto de la respuesta
        if hasattr(respuesta, "content"):
            return str(respuesta.content)
        return str(respuesta)
