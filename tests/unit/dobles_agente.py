"""Dobles de prueba para el agente de IA (spec 009).

ModeloDoble retorna una SalidaAgente predefinida.
ModeloDobleInvalido retorna JSON malformado para probar AC-AGT-03.
ContadorDoble es un contador in-memory con reloj inyectado.
entrada_agente_ejemplo() construye una EntradaAgente mínima.
"""

from __future__ import annotations

from datetime import date

from src.level2_agent.agente.modelos import (
    EntradaAgente,
    ResultadoAgente,
    SalidaAgente,
)
from src.level2_agent.banderas.modelos import EstadosAutenticacion
from src.level2_agent.models import EmailData
from src.level3_logic.scoring.modelos import ScoreFinal


class ModeloDoble:
    """Modelo simulado que retorna una SalidaAgente predefinida.

    AC-AGT-06: cero llamadas al modelo real.
    """

    def __init__(self, salida: SalidaAgente | None = None) -> None:
        self._salida = salida or SalidaAgente(
            resumen="Resumen de prueba",
            analisis_tecnico="Análisis técnico de prueba",
            es_phishing=True,
            indicadores_phishing=["indicador_test"],
            nivel_severidad="Alto",
            justificacion_veredicto="Justificación de prueba",
        )
        self.llamadas: list[str] = []

    def invocar(self, prompt: str, *, herramientas: list[object] | None = None) -> str:
        """Retorna la salida predefinida como JSON string."""
        self.llamadas.append(prompt)
        return self._salida.model_dump_json()


class ModeloDobleInvalido:
    """Modelo simulado que retorna JSON malformado.

    AC-AGT-03: salida invalidada → 1 reintento → revision_manual.
    """

    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def invocar(self, prompt: str, *, herramientas: list[object] | None = None) -> str:
        """Retorna JSON malformado."""
        self.llamadas.append(prompt)
        return "esto no es json valido {{"


class ContadorDoble:
    """Contador in-memory con reloj inyectado para pruebas.

    AC-AGT-05: probar tope N-1/N/N+1 sin MongoDB.
    """

    def __init__(self, *, max_diario: int = 100, ahora: date | None = None) -> None:
        self._max_diario = max_diario
        self._hoy = ahora or date.today()
        self._conteo = 0

    def disponible(self) -> bool:
        return self._conteo < self._max_diario

    def incrementar(self) -> int:
        self._conteo += 1
        return self._conteo

    @property
    def conteo(self) -> int:
        return self._conteo

    @property
    def max_diario(self) -> int:
        return self._max_diario


def entrada_agente_ejemplo(
    *,
    score: int = 50,
    email_data: EmailData | None = None,
) -> EntradaAgente:
    """Construye una EntradaAgente mínima con valores por defecto."""
    return EntradaAgente(
        email_data=email_data or EmailData(),
        score_final=ScoreFinal(
            score_final=score,
            score_clasificador=float(score),
            puntos_banderas=0,
            version_modelo="test",
        ),
        banderas_cabeceras=[],
        estados_autenticacion=EstadosAutenticacion(),
        resultado_adjuntos=[],
        resultados_vt=[],
    )
