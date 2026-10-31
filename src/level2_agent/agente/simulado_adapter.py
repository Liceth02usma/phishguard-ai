"""Adapter simulado del modelo LLM (spec 009, FR-008).

Retorna una SalidaAgente predefinida sin llamar a ningún servicio.
Usado en tests (AC-AGT-06), CI, y modo dry-run del agente.
Implementa el Protocol ModeloLLM.
"""

from __future__ import annotations

import os

from src.level2_agent.agente.modelos import (
    LLM_MODELO_DEFAULT,
    SalidaAgente,
)


class SimuladoAdapter:
    """Adapter simulado que retorna una SalidaAgente predefinida.

    Cero llamadas a servicios externos. Útil para:
    - Tests unitarios (AC-AGT-06)
    - CI sin credenciales
    - Modo dry-run del pipeline
    """

    def __init__(self, *, salida: SalidaAgente | None = None) -> None:
        self._modelo_nombre = os.environ.get("LLM_MODELO", LLM_MODELO_DEFAULT)
        self._salida = salida or SalidaAgente(
            resumen="Análisis simulado: no se consultó modelo real.",
            analisis_tecnico="Modo simulado activo. Sin llamada a LLM.",
            es_phishing=False,
            indicadores_phishing=[],
            nivel_severidad="Bajo",
            justificacion_veredicto="Veredicto simulado sin consulta al modelo.",
        )
        self.llamadas: list[str] = []

    def invocar(self, prompt: str, *, herramientas: list[object] | None = None) -> str:
        """Retorna la salida predefinida como JSON string."""
        self.llamadas.append(prompt)
        return self._salida.model_dump_json()
