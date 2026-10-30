"""Adapter del modelo Gemini para el agente (spec 009, M07, FR-008).

Implementa el Protocol ModeloLLM. Se construye solo cuando se necesita
(el orquestador lo importa lazy). El modelo y temperatura son configurables
via LLM_MODELO env var.
"""

from __future__ import annotations

import os
from typing import Any

from src.level2_agent.agente.modelos import (
    LLM_MODELO_DEFAULT,
    LLM_TEMPERATURA,
)


class GeminiAdapter:
    """Adapter del modelo Gemini que implementa ModeloLLM.

    Envuelve ChatGoogleGenerativeAI de langchain-google-genai.
    Temperatura 0 para determinismo máximo.
    """

    def __init__(self, *, modelo: str | None = None) -> None:
        self._modelo_nombre = modelo or os.environ.get(
            "LLM_MODELO", LLM_MODELO_DEFAULT
        )
        self._llm: Any = None

    def _construir_llm(self) -> Any:
        """Construye la instancia de ChatGoogleGenerativeAI (lazy)."""
        if self._llm is not None:
            return self._llm

        from langchain_google_genai import ChatGoogleGenerativeAI

        self._llm = ChatGoogleGenerativeAI(
            model=self._modelo_nombre,
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
